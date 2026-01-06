"""
Celery configuration for CPU-intensive background tasks.
Separates web layer from processing layer for predictable performance.
"""

import os
from celery import Celery

# Redis connection for Celery broker and result backend
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "eeg_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.eeg_processing"]
)

# Celery configuration
celery_app.conf.update(
    # Performance settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Worker settings for CPU-bound tasks
    worker_prefetch_multiplier=1,  # Disable prefetch for CPU-heavy tasks
    worker_max_tasks_per_child=1000,  # Recycle workers periodically
    
    # PERFORMANCE: Disable result backend for fire-and-forget tasks
    # Saves Redis writes and reduces latency
    task_ignore_result=True,
    task_store_errors_even_if_ignored=False,
    
    # Redis connection pool for better concurrency
    broker_connection_retry_on_startup=True,
    broker_pool_limit=20,  # Connection pool size
    
    # Task execution settings
    task_soft_time_limit=30,  # Kill tasks after 30 seconds
    task_time_limit=45,  # Hard limit at 45 seconds
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,
    task_track_started=True,
)

if __name__ == "__main__":
    celery_app.start()
