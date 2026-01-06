#!/bin/bash
# Diagnostic script to check if Celery + Redis optimizations are working

echo "════════════════════════════════════════════════════════════════"
echo "🔍 NIURA EEG SERVICE DIAGNOSTIC REPORT"
echo "════════════════════════════════════════════════════════════════"
echo ""

# 1. Check if containers are running
echo "📦 1. CONTAINER STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd ../
docker-compose ps | grep -E "redis|eeg-service|eeg-worker"
echo ""

# 2. Check Redis connectivity
echo "🔴 2. REDIS CONNECTIVITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "✅ Redis is responding: PONG"
else
    echo "❌ Redis is NOT responding"
fi
echo ""

# 3. Check if Celery worker is alive
echo "⚙️  3. CELERY WORKER STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if docker-compose ps eeg-worker 2>/dev/null | grep -q "Up"; then
    echo "✅ Worker container is UP"
    echo ""
    echo "Checking worker connectivity..."
    docker-compose exec -T eeg-worker celery -A app.core.celery_app inspect ping 2>/dev/null || echo "❌ Worker not responding to ping"
else
    echo "❌ Worker container is NOT running"
fi
echo ""

# 4. Check Redis queue length
echo "📊 4. CELERY QUEUE LENGTH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
queue_length=$(docker-compose exec -T redis redis-cli LLEN celery 2>/dev/null)
if [[ -n "$queue_length" ]]; then
    echo "Queue 'celery': $queue_length tasks waiting"
    if [[ $queue_length -gt 100 ]]; then
        echo "⚠️  WARNING: Queue is backing up! Worker may be too slow."
    fi
else
    echo "❌ Cannot check queue (Redis issue?)"
fi
echo ""

# 5. Check environment variables
echo "🔧 5. ENVIRONMENT VARIABLES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
redis_url=$(docker-compose exec -T eeg-service env | grep REDIS_URL 2>/dev/null)
if [[ -n "$redis_url" ]]; then
    echo "✅ REDIS_URL is set: $redis_url"
else
    echo "❌ REDIS_URL is NOT set in eeg-service"
fi
echo ""

# 6. Check EEG service logs for errors
echo "📝 6. RECENT EEG SERVICE LOGS (last 10 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker-compose logs --tail=10 eeg-service 2>/dev/null
echo ""

# 7. Check worker logs for activity
echo "📝 7. RECENT WORKER LOGS (last 10 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if docker-compose ps eeg-worker 2>/dev/null | grep -q "Up"; then
    docker-compose logs --tail=10 eeg-worker 2>/dev/null
else
    echo "❌ Worker not running - no logs available"
fi
echo ""

# 8. Test endpoint response
echo "🧪 8. ENDPOINT TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Testing /api/bulk-fft endpoint..."
response=$(curl -s -X POST http://localhost:8002/api/bulk-fft \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"duration":2,"records":[{"sample_index":0,"timestamp":"2025-01-01T00:00:00Z","eeg":[0.1,0.2,0.3,0.4]}]}' \
  2>&1)

if echo "$response" | grep -q "task_id"; then
    echo "✅ Endpoint returned task_id (NEW optimized version)"
    echo "Response: $response"
else
    echo "⚠️  Response does NOT contain task_id (may be using OLD version)"
    echo "Response: $response"
fi
echo ""

# 9. Check Docker image build date
echo "🐋 9. DOCKER IMAGE INFO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
eeg_image=$(docker-compose ps -q eeg-service 2>/dev/null)
if [[ -n "$eeg_image" ]]; then
    echo "EEG Service image created:"
    docker inspect $eeg_image | grep Created | head -1
else
    echo "❌ Cannot find eeg-service container"
fi

worker_image=$(docker-compose ps -q eeg-worker 2>/dev/null)
if [[ -n "$worker_image" ]]; then
    echo "Worker image created:"
    docker inspect $worker_image | grep Created | head -1
else
    echo "❌ Cannot find eeg-worker container"
fi
echo ""

# 10. Summary
echo "════════════════════════════════════════════════════════════════"
echo "📋 DIAGNOSTIC SUMMARY"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Check the results above. Common issues:"
echo ""
echo "❌ If Redis is not responding:"
echo "   → Run: ./niura-local.sh redis-start"
echo ""
echo "❌ If worker is not running:"
echo "   → Run: ./niura-local.sh start-worker"
echo ""
echo "❌ If endpoint doesn't return task_id:"
echo "   → Code changes not deployed. Run: ./niura-local.sh rebuild-eeg"
echo ""
echo "❌ If worker not in container list:"
echo "   → Run: ./niura-local.sh build-worker && ./niura-local.sh start-worker"
echo ""
echo "❌ If REDIS_URL not set:"
echo "   → Edit backEnd/eeg-service/.env and add: REDIS_URL=redis://redis:6379/0"
echo "   → Then: ./niura-local.sh restart-eeg"
echo ""
echo "════════════════════════════════════════════════════════════════"
