#!/bin/bash

# ============================================================================
# Celery Worker Startup Script
# ============================================================================
# Starts Celery worker for CPU-intensive EEG processing
#
# Usage:
#   ./start-worker.sh
#
# Environment Variables:
#   REDIS_URL - Redis broker URL (default: redis://localhost:6379/0)
#   WORKERS - Number of worker processes (default: 4)
# ============================================================================

set -e

WORKERS=${CELERY_WORKERS:-4}
REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}

echo "🔧 Starting Celery Worker for EEG Processing"
echo "   Workers: $WORKERS"
echo "   Broker: $REDIS_URL"
echo "   Queue: eeg_processing"
echo ""

# Check Redis connectivity
if ! python -c "import redis; r=redis.Redis.from_url('$REDIS_URL'); r.ping()" 2>/dev/null; then
    echo "❌ Error: Cannot connect to Redis at $REDIS_URL"
    echo "   Start Redis with: docker run -d -p 6379:6379 redis:7-alpine"
    exit 1
fi

echo "✅ Redis connection OK"
echo ""

# Start Celery worker
exec celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency="$WORKERS" \
    --prefetch-multiplier=1 \
    -Q eeg_processing \
    --max-tasks-per-child=1000
