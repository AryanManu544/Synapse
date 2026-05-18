#!/bin/sh
set -eu

# Render free tier has no Background Workers — run Celery beside Uvicorn in one service.
celery -A app.celery_app worker --loglevel=info -Q reviews &

exec uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips "*"
