"""Rolling-origin backtest, then fit the served model on all history."""

import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from . import __version__
from .features import FEATURES, HORIZON, add_features, wape
from .simulate import simulate

FOLDS = 6
PARAMS = {
    "objective": "poisson", "learning_rate": 0.05, "num_leaves": 63, "n_estimators": 250,
    "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "min_child_samples": 30,
    "verbose": -1, "random_state": 42, "n_jobs": 2,
}
Q_PARAMS = {**PARAMS, "objective": "quantile", "alpha": 0.9, "n_estimators": 150}


def fit(frame: pd.DataFrame, params: dict) -> lgb.LGBMRegressor:
    usable = frame[frame["stocked_out"] == 0].dropna(subset=["mean_28"])
    return lgb.LGBMRegressor(**params).fit(usable[FEATURES], usable["sales"])


def backtest(frame: pd.DataFrame) -> dict:
    last = frame["date"].max()
    results = []
    for fold in range(FOLDS):
        end = last - pd.Timedelta(days=fold * HORIZON)
        start = end - pd.Timedelta(days=HORIZON - 1)
        train_rows = frame[frame["date"] < start]
        test = frame[(frame["date"] >= start) & (frame["date"] <= end)]
        point = np.clip(fit(train_rows, PARAMS).predict(test[FEATURES]), 0, None)
        upper = np.clip(fit(train_rows, Q_PARAMS).predict(test[FEATURES]), 0, None)
        actual = test["true_demand"].to_numpy()
        naive = test["lag_7"].fillna(test["mean_28"]).fillna(0).to_numpy()
        results.append(
            {
                "start": str(start.date()),
                "model_wape": wape(actual, point),
                "seasonal_naive_wape": wape(actual, naive),
                "p90_coverage": float((actual <= upper).mean() * 100),
            }
        )
    frame_out = pd.DataFrame(results)
    return {
        "folds": results,
        "model_wape": round(frame_out["model_wape"].mean(), 2),
        "seasonal_naive_wape": round(frame_out["seasonal_naive_wape"].mean(), 2),
        "p90_coverage": round(frame_out["p90_coverage"].mean(), 1),
    }


def main() -> None:
    raw = simulate()
    frame = add_features(raw)
    report = {
        "data": "synthetic (src/retailcast/simulate.py)",
        "rows": len(raw),
        "series": int(raw.groupby(["store_id", "item_id"]).ngroups),
        "stockout_day_percent": round(float((raw["stock_end"] == 0).mean() * 100), 2),
        "sales_understate_demand_percent": round(
            float((1 - raw["sales"].sum() / raw["true_demand"].sum()) * 100), 2
        ),
        **backtest(frame),
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/backtest.json").write_text(json.dumps(report, indent=2))
    Path("models").mkdir(exist_ok=True)
    history = frame[frame["date"] < frame["date"].max() - pd.Timedelta(days=HORIZON - 1)]
    joblib.dump(
        # The last week stays unseen so the dashboard can show forecast against actuals.
        {"point": fit(history, PARAMS), "upper": fit(history, Q_PARAMS), "version": __version__},
        "models/forecast.joblib",
        compress=3,
    )
    print(json.dumps({k: v for k, v in report.items() if k != "folds"}, indent=2))


if __name__ == "__main__":
    main()
