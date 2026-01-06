#!/bin/bash

# ============================================================================
# Production Startup Script for EEG Service
# ============================================================================
# Runs Uvicorn with optimal performance settings for production
#
# Usage:
#   ./start-production.sh
#
# Environment Variables:
#   PORT - Server port (default: 8002)
#   WORKERS - Number of workers (default: 4)
#   HOST - Bind host (default: 0.0.0.0)
# ============================================================================

set -e

# Configuration
PORT=${PORT:-8002}
WORKERS=${WORKERS:-4}
HOST=${HOST:-0.0.0.0}
BACKLOG=${BACKLOG:-2048}
LIMIT_CONCURRENCY=${LIMIT_CONCURRENCY:-1000}

echo "🚀 Starting EEG Service in PRODUCTION mode"
echo "   Workers: $WORKERS"
echo "   Port: $PORT"
echo "   Backlog: $BACKLOG"
echo "   Max Concurrency: $LIMIT_CONCURRENCY"
echo ""

# Check if uvloop is installed
if ! python -c "import uvloop" 2>/dev/null; then
    echo "⚠️  Warning: uvloop not installed. Install with: pip install uvloop"
    echo "   Performance will be degraded without uvloop"
fi

# Check if Redis is accessible
if ! python -c "import redis; r=redis.Redis.from_url('${REDIS_URL:-redis://localhost:6379/0}'); r.ping()" 2>/dev/null; then
    echo "⚠️  Warning: Redis not accessible at ${REDIS_URL:-redis://localhost:6379/0}"
    echo "   Celery tasks will fail. Start Redis with: docker run -d -p 6379:6379 redis:7-alpine"
fi

echo "✅ Pre-flight checks complete"
echo ""

# Start Uvicorn with production settings
exec uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --loop uvloop \
    --http httptools \
    --no-access-log \
    --backlog "$BACKLOG" \
    --limit-concurrency "$LIMIT_CONCURRENCY" \
    --log-level info
