"""REST API and static dashboard host."""

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .planner import build_snapshot

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend/dist"


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            created_at TEXT NOT NULL
        )"""
    )
    return db


@asynccontextmanager
async def lifespan(app: FastAPI):
    snapshot_path = os.getenv("SNAPSHOT_PATH")
    if snapshot_path:
        app.state.snapshot = json.loads(Path(snapshot_path).read_text())
    else:
        bundle = joblib.load(os.getenv("MODEL_PATH", ROOT / "models/forecast.joblib"))
        app.state.snapshot = build_snapshot(bundle)
    app.state.db = connect(os.getenv("DB_PATH", "orders.db"))
    yield
    app.state.db.close()


app = FastAPI(title="RetailCast", version=__version__, lifespan=lifespan)


class OrderIn(BaseModel):
    store_id: str
    item_id: str
    quantity: int = Field(gt=0, le=100_000)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/readyz")
def readyz(request: Request) -> dict:
    return {"status": "ready", "rows": len(request.app.state.snapshot["rows"])}


@app.get("/api/recommendations")
def recommendations(
    request: Request,
    store_id: str | None = None,
    risk: str | None = Query(None, pattern="^(high|medium|low)$"),
) -> dict:
    snapshot = request.app.state.snapshot
    rows = [
        row for row in snapshot["rows"]
        if (store_id is None or row["store_id"] == store_id)
        and (risk is None or row["risk"] == risk)
    ]
    rank = {"high": 0, "medium": 1, "low": 2}
    rows.sort(key=lambda r: (rank[r["risk"]], -r["order_quantity"]))
    return {"as_of": snapshot["as_of"], "rows": rows}


@app.get("/api/forecast/{store_id}/{item_id}")
def forecast(request: Request, store_id: str, item_id: str) -> list[dict]:
    series = request.app.state.snapshot["daily"].get(f"{store_id}/{item_id}")
    if series is None:
        raise HTTPException(404, "unknown store or item")
    return series


@app.post("/api/orders", status_code=201)
def create_order(request: Request, order: OrderIn) -> dict:
    if f"{order.store_id}/{order.item_id}" not in request.app.state.snapshot["daily"]:
        raise HTTPException(404, "unknown store or item")
    created = datetime.now(UTC).isoformat(timespec="seconds")
    db = request.app.state.db
    with db:
        cursor = db.execute(
            "INSERT INTO orders (store_id, item_id, quantity, created_at) VALUES (?, ?, ?, ?)",
            (order.store_id, order.item_id, order.quantity, created),
        )
    return {"id": cursor.lastrowid, **order.model_dump(), "created_at": created}


@app.get("/api/orders")
def list_orders(request: Request) -> list[dict]:
    rows = request.app.state.db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100")
    return [dict(row) for row in rows]


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(DIST / "index.html")
