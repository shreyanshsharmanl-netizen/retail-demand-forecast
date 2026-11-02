import json

import pytest
from fastapi.testclient import TestClient

from retailcast.api import app

SNAPSHOT = {
    "as_of": "2026-01-01",
    "rows": [
        {"store_id": "1", "item_id": "A", "risk": "low", "order_quantity": 0},
        {"store_id": "1", "item_id": "B", "risk": "high", "order_quantity": 9},
        {"store_id": "2", "item_id": "A", "risk": "high", "order_quantity": 20},
    ],
    "daily": {"1/A": [{"date": "2026-01-02", "forecast": 3.0, "upper": 5.0, "actual": 4}],
              "1/B": [], "2/A": []},
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = tmp_path / "s.json"
    path.write_text(json.dumps(SNAPSHOT))
    monkeypatch.setenv("SNAPSHOT_PATH", str(path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_highest_risk_and_largest_order_first(client):
    rows = client.get("/api/recommendations").json()["rows"]
    assert [(r["store_id"], r["item_id"]) for r in rows] == [("2", "A"), ("1", "B"), ("1", "A")]


def test_filters(client):
    assert len(client.get("/api/recommendations?store_id=1&risk=high").json()["rows"]) == 1
    assert client.get("/api/recommendations?risk=urgent").status_code == 422


def test_forecast_lookup(client):
    assert client.get("/api/forecast/1/A").json()[0]["actual"] == 4
    assert client.get("/api/forecast/9/Z").status_code == 404


def test_order_is_saved(client):
    response = client.post("/api/orders", json={"store_id": "1", "item_id": "A", "quantity": 5})
    assert response.status_code == 201
    assert client.get("/api/orders").json()[0]["quantity"] == 5


@pytest.mark.parametrize("quantity", [0, -3, 1_000_000])
def test_invalid_quantity_rejected(client, quantity):
    body = {"store_id": "1", "item_id": "A", "quantity": quantity}
    assert client.post("/api/orders", json=body).status_code == 422


def test_order_for_unknown_item_rejected(client):
    body = {"store_id": "9", "item_id": "Z", "quantity": 1}
    assert client.post("/api/orders", json=body).status_code == 404
