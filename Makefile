check:
	ruff check . && pytest && cd frontend && npm test
train:
	PYTHONPATH=src python -m retailcast.train
web:
	cd frontend && npm ci && npm run build
serve:
	PYTHONPATH=src uvicorn retailcast.api:app --reload
