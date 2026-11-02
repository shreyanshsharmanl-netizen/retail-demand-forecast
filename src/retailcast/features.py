"""Feature engineering without leaking future data."""

import numpy as np
import pandas as pd

HORIZON = 7
CATEGORICAL = ["store_id", "item_id", "category"]
FEATURES = CATEGORICAL + [
    "weekday", "month", "promo", "holiday", "lag_7", "lag_14", "lag_28",
    "mean_7", "mean_28", "stockout_rate_28",
]


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Every lag is at least HORIZON days old, so it is known at forecast time.

    Days that ended with no stock are masked before lags are computed, because
    their sales understate demand.
    """
    out = frame.sort_values(["store_id", "item_id", "date"]).copy()
    out["stocked_out"] = (out["stock_end"] == 0).astype(int)
    out["clean_sales"] = out["sales"].where(out["stocked_out"] == 0)
    group = out.groupby(["store_id", "item_id"], sort=False)
    for lag in (7, 14, 28):
        out[f"lag_{lag}"] = group["clean_sales"].shift(lag)
    shifted = group["clean_sales"].shift(HORIZON)
    keys = [out["store_id"], out["item_id"]]
    out["mean_7"] = shifted.groupby(keys).transform(lambda s: s.rolling(7, min_periods=3).mean())
    out["mean_28"] = shifted.groupby(keys).transform(lambda s: s.rolling(28, min_periods=7).mean())
    out["stockout_rate_28"] = (
        group["stocked_out"].shift(HORIZON).groupby(keys)
        .transform(lambda s: s.rolling(28, min_periods=7).mean())
    )
    out["weekday"] = out["date"].dt.dayofweek
    out["month"] = out["date"].dt.month
    for column in CATEGORICAL:
        out[column] = out[column].astype("category")
    return out


def wape(actual: np.ndarray, forecast: np.ndarray) -> float:
    """Weighted absolute percentage error: total error over total volume."""
    return float(np.abs(actual - forecast).sum() / np.maximum(actual.sum(), 1) * 100)
