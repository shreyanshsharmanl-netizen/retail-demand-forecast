# Test plan

| Level | What | Where | When |
|-------|------|-------|------|
| Unit | Simulator invariants, leakage, stockout masking, WAPE, planner | `tests/test_core.py` | Every push |
| API | Ranking, filters, orders, bad input | `tests/test_api.py` | Every push |
| Frontend | Chart scaling and empty data | `frontend/src/chart.test.js` | Every push |
| Container | Image builds and reaches `/readyz` | CI `image` job | Every push |
| Model | Rolling backtest against baseline | `make train` | Each new model |
| Manual | Filter, select an item, place an order | Demo | Each release |
