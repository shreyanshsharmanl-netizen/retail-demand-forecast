FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json .
RUN npm ci
COPY frontend .
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home app && mkdir /data && chown app /data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src src
COPY models models
COPY --from=web /web/dist frontend/dist
USER app
ENV PYTHONPATH=/app/src DB_PATH=/data/orders.db PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn retailcast.api:app --host 0.0.0.0 --port ${PORT}"]
