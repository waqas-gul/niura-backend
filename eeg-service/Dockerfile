FROM python:3.11.13-slim-bookworm

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

# ============================================================================
# PRODUCTION-OPTIMIZED UVICORN CONFIGURATION
# ============================================================================
# Performance tuning:
# - Multiple workers (CPU cores - 1, min 2) for parallel request handling
# - uvloop for 2-4x faster event loop performance
# - httptools for faster HTTP protocol parsing (C extension)
# - No --reload (dev-only feature, hurts performance)
# - Access logs disabled to reduce I/O overhead in hot path
# - Backlog increased for high-concurrency scenarios
# ============================================================================

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8002", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--no-access-log", \
     "--backlog", "2048", \
     "--limit-concurrency", "1000"]
