from celery import Celery
from core.config import settings

# Initialize Celery app
celery_app = Celery(
    "ntier_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Configuration overrides
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Auto-discover tasks as we add them to services
    imports=[
        "services.news_monitor",
        "services.ingestion_tasks"
    ]
)

# Optional: Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "poll-news-every-hour": {
        "task": "services.news_monitor.poll_news_task",
        "schedule": 3600.0, # every hour
    },
}
