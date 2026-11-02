import numpy as np
import pandas as pd
import pytest

from retailcast.features import add_features, wape
from retailcast.planner import recommend
from retailcast.simulate import simulate


@pytest.fixture(scope="module")
def raw():
    return simulate(days=120, stores=1)


def test_simulation_is_reproducible(raw):
    pd.testing.assert_frame_equal(raw, simulate(days=120, stores=1))


def test_sales_never_exceed_demand(raw):
    assert (raw["sales"] <= raw["true_demand"]).all()
    assert (raw["stock_end"] >= 0).all()


def test_lags_cannot_see_the_forecast_week(raw):
    """Changing the last seven days must not change their features."""
    last = raw["date"].max()
    changed = raw.copy()
    week = changed["date"] > last - pd.Timedelta(days=7)
    changed.loc[week, "sales"] += 1000
    columns = ["lag_7", "lag_14", "lag_28", "mean_7", "mean_28"]
    last - pd.Timedelta(days=7)
    before = add_features(raw).query("date > @cutoff")[columns]
    after = add_features(changed).query("date > @cutoff")[columns]
    pd.testing.assert_frame_equal(before, after)


def test_stockout_days_are_excluded_from_lags():
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=10),
            "store_id": 1, "item_id": "A", "category": "C",
            "sales": [5] * 10, "stock_end": [0, 9, 9, 9, 9, 9, 9, 9, 9, 9],
        }
    )
    assert np.isnan(add_features(frame)["lag_7"].iloc[7])


def test_wape():
    assert wape(np.array([10, 10]), np.array([8, 12])) == 20


def test_low_stock_is_high_risk_and_orders():
    result = recommend(np.full(7, 10.0), np.full(7, 14.0), stock=5)
    assert result["risk"] == "high"
    assert result["order_quantity"] == 76  # 70 + sqrt(7 * 16) = 80.6, less 5


def test_plenty_of_stock_orders_nothing():
    result = recommend(np.full(7, 10.0), np.full(7, 14.0), stock=500)
    assert (result["risk"], result["order_quantity"]) == ("low", 0)


def test_medium_risk_between_lead_time_and_week():
    assert recommend(np.full(7, 10.0), np.full(7, 11.0), stock=40)["risk"] == "medium"
