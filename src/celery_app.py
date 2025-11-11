from celery import Celery
from src.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

# Create Celery app
celery_app = Celery(
    "rag_boilerplate_ingestion",
    broker=f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}" if REDIS_PASSWORD else f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    backend=f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}" if REDIS_PASSWORD else f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    include=["src.distributed_task.ingestion_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=24 * 60 * 60,  # 24 hours
    task_soft_time_limit=23 * 60 * 60,  # 23 hours
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_ignore_result=False,
    result_expires=3600,  # 1 hour
)
