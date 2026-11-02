# Requirements

## Problem
Stores lose sales when shelves run empty and lose money when they over-order. Managers need to know what to order this week, and which items are at risk first.

## Users
- **Store manager:** reviews risky items and places orders.
- **Analyst:** checks forecast accuracy.

## Functional requirements
| ID | Requirement | Verified by |
|----|-------------|-------------|
| F1 | Forecast each store-item for seven days with a P90 upper bound | `planner.py`, dashboard |
| F2 | Rank items by stockout risk, then order size | `test_highest_risk_and_largest_order_first` |
| F3 | Filter by store and risk | `test_filters` |
| F4 | Save an order and reject invalid ones | `test_order_is_saved`, `test_invalid_quantity_rejected` |
| F5 | Compare forecast with actual demand per item | Dashboard chart |

## Non-functional requirements
| ID | Requirement | Status |
|----|-------------|--------|
| N1 | Beat a seasonal-naive forecast in backtests | `reports/backtest.json` |
| N2 | No future data in features | `test_lags_cannot_see_the_forecast_week` |
| N3 | Stockout days do not bias history | `test_stockout_days_are_excluded_from_lags` |
| N4 | P90 bound covers roughly 90% of days | `reports/backtest.json` |

## Limits
- Store data is simulated. Accuracy on a real store is unknown.
- Promotions and holidays are assumed known in advance.
- The order table has no login. Real use needs authentication and a server database.
