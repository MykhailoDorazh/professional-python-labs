# syntax=docker/dockerfile:1

# ---------- stage 1: build the wheel ----------
FROM python:3.13-slim AS builder
WORKDIR /build
RUN python -m pip install --no-cache-dir --root-user-action=ignore build==1.3.0
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m build --wheel --outdir /dist

# ---------- stage 2: runtime image ----------
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="bank-account-service" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Дораж Михайло"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    APP_ENV=production \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_URL=sqlite:////app/data/bank.db

WORKDIR /app
COPY --from=builder /dist/*.whl /tmp/
RUN python -m pip install /tmp/*.whl && rm /tmp/*.whl \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser
VOLUME ["/app/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# apply Alembic migrations, then start uvicorn (no --reload in production)
CMD ["bank-account-service", "serve", "--migrate"]
