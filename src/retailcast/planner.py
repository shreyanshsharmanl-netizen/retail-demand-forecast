"""Turn a seven-day forecast into reorder recommendations."""

import math

import numpy as np
import pandas as pd

from .features import CATEGORICAL, FEATURES, HORIZON, add_features
from .simulate import LEAD_TIME_DAYS, simulate


def recommend(point: np.ndarray, upper: np.ndarray, stock: int) -> dict:
    """Stock up to expected demand plus a safety buffer for the week.

    Daily P90 margins are combined in quadrature because errors on different
    days partly cancel. Adding them directly would overstate the buffer.
    """
    expected = float(point.sum())
    safety = math.sqrt(float(np.square(np.maximum(upper - point, 0)).sum()))
    during_lead_time = float(point[:LEAD_TIME_DAYS].sum())
    days_of_cover = stock / max(expected / len(point), 0.01)
    if stock < during_lead_time:
        risk = "high"
    elif stock < expected:
        risk = "medium"
    else:
        risk = "low"
    return {
        "forecast_7d": round(expected, 1),
        "safety_stock": round(safety, 1),
        "order_quantity": max(0, math.ceil(expected + safety - stock)),
        "days_of_cover": round(days_of_cover, 1),
        "risk": risk,
    }


def build_snapshot(bundle: dict, frame: pd.DataFrame | None = None) -> dict:
    """Forecast the final week from the stock level the day before it starts."""
    frame = add_features(simulate() if frame is None else frame)
    as_of = frame["date"].max() - pd.Timedelta(days=HORIZON)
    week = frame[frame["date"] > as_of].copy()
    week["forecast"] = np.clip(bundle["point"].predict(week[FEATURES]), 0, None)
    week["upper"] = np.clip(bundle["upper"].predict(week[FEATURES]), 0, None)
    for column in CATEGORICAL:
        week[column] = week[column].astype(str)
    stock = frame[frame["date"] == as_of].copy()
    for column in CATEGORICAL:
        stock[column] = stock[column].astype(str)
    stock = stock.set_index(["store_id", "item_id"])["stock_end"]

    rows, daily = [], {}
    for (store, item), group in week.groupby(["store_id", "item_id"]):
        group = group.sort_values("date")
        rows.append(
            {
                "store_id": store,
                "item_id": item,
                "category": group["category"].iloc[0],
                "stock": int(stock[(store, item)]),
                "actual_7d": int(group["true_demand"].sum()),
                **recommend(
                    group["forecast"].to_numpy(), group["upper"].to_numpy(),
                    int(stock[(store, item)]),
                ),
            }
        )
        daily[f"{store}/{item}"] = [
            {
                "date": str(day.date()),
                "forecast": round(float(point), 1),
                "upper": round(float(high), 1),
                "actual": int(actual),
            }
            for day, point, high, actual in zip(
                group["date"], group["forecast"], group["upper"], group["true_demand"],
                strict=True,
            )
        ]
    return {"as_of": str(as_of.date()), "rows": rows, "daily": daily}
