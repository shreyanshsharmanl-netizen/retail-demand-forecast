"""Synthetic grocery store history with known true demand.

Daily demand depends on weekly and yearly seasonality, a holiday lift, promos
and item popularity. Sales are capped by stock on hand, so a stockout hides real
demand, exactly as in a store's own sales records. Keeping true demand lets us
measure whether the forecast sees through that censoring.
"""

import numpy as np
import pandas as pd

CATEGORIES = {
    "Dairy": (34, 0.18, 5),
    "Produce": (46, 0.30, 3),
    "Bakery": (28, 0.22, 3),
    "Pantry": (20, 0.10, 21),
    "Frozen": (16, -0.25, 21),
    "Beverages": (30, -0.35, 14),
}
WEEKDAY = np.array([0.82, 0.78, 0.85, 0.95, 1.2, 1.45, 0.95])
HOLIDAYS = ["12-23", "12-24", "12-31", "07-01", "10-11", "04-05"]
ITEMS_PER_CATEGORY = 8
LEAD_TIME_DAYS = 3


def simulate(days: int = 900, stores: int = 3, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    day_of_year = dates.dayofyear.to_numpy()
    holiday = np.isin(dates.strftime("%m-%d"), HOLIDAYS)
    frames = []
    for store in range(1, stores + 1):
        store_scale = rng.uniform(0.75, 1.3)
        for category, (base, winter, cover) in CATEGORIES.items():
            for index in range(1, ITEMS_PER_CATEGORY + 1):
                popularity = rng.lognormal(0, 0.45) * store_scale
                season = 1 + winter * np.cos(2 * np.pi * (day_of_year - 15) / 365)
                promo = rng.random(days) < 0.06
                expected = (
                    base * popularity * season * WEEKDAY[dates.dayofweek]
                    * np.where(promo, rng.uniform(1.4, 2.2), 1)
                    * np.where(holiday, 1.5, 1)
                    * (1 + 0.0001 * np.arange(days))
                )
                demand = rng.negative_binomial(8, 8 / (8 + expected))
                sales, stock_end = _replenish(rng, demand, base * popularity, cover)
                frames.append(
                    pd.DataFrame(
                        {
                            "date": dates,
                            "store_id": store,
                            "item_id": f"{category[:3].upper()}-{index:02d}",
                            "category": category,
                            "promo": promo.astype(int),
                            "holiday": holiday.astype(int),
                            "true_demand": demand,
                            "sales": sales,
                            "stock_end": stock_end,
                        }
                    )
                )
    return pd.concat(frames, ignore_index=True)


def _replenish(rng, demand: np.ndarray, level: float, cover: int):
    """Min-max ordering with lead time. A late truck can cause a stockout."""
    reorder_point = level * (LEAD_TIME_DAYS + 3)  # lead-time demand plus safety stock
    target = reorder_point + level * cover
    stock, pipeline = target, []
    sales, closing = np.zeros(len(demand), int), np.zeros(len(demand), int)
    for day, wanted in enumerate(demand):
        stock += sum(q for arrival, q in pipeline if arrival == day)
        pipeline = [p for p in pipeline if p[0] > day]
        sales[day] = min(wanted, stock)
        stock -= sales[day]
        closing[day] = stock
        on_order = sum(q for _, q in pipeline)
        if stock + on_order < reorder_point:
            delay = LEAD_TIME_DAYS + (rng.random() < 0.15) * rng.integers(1, 4)
            pipeline.append((day + delay, target - stock - on_order))
    return sales, closing
