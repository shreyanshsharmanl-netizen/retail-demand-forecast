# Runbook

## Deploy
Pushes to `main` redeploy on Render through `render.yaml`. Start-up builds the forecast snapshot, so allow up to a minute before `/readyz` passes.

## Data persistence
SQLite lives at `DB_PATH`. Render's free plan has no persistent disk, so demo orders reset on restart.

## Troubleshooting
| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Slow start | Snapshot building on a small instance | Precompute it and set `SNAPSHOT_PATH` |
| Blank page | Frontend missing from the image | Check the `web` build stage |
| Backtest error rises | Demand pattern changed or a bug in features | Compare folds in `reports/backtest.json` |

## Roll back
Redeploy the previous Render deploy, or the previous `vX.Y.Z` image.
