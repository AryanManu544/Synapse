# syntax=docker/dockerfile:1

# ------------------------------------------------------------------------------
# Builder: install dependencies into an isolated virtual environment
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY pyproject.toml ./
COPY main.py ./
COPY app ./app

RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

# ------------------------------------------------------------------------------
# Runtime: minimal image with non-root user
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    LOG_FORMAT=json \
    ENVIRONMENT=production

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 synapse \
    && useradd --system --uid 10001 --gid synapse --home-dir /app synapse

COPY --from=builder /opt/venv /opt/venv
COPY --chown=synapse:synapse main.py ./
COPY --chown=synapse:synapse app ./app

USER synapse

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
