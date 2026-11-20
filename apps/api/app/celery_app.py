"""Celery application. The worker and beat services both import this module."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "gapscout",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "close-outreach-windows-daily": {
            "task": "gapscout.close_outreach_windows_task",
            "schedule": 86400.0,  # Run daily
            "args": (14,),
        },
        "cleanup-expired-raw-data-daily": {
            "task": "gapscout.cleanup_expired_raw_data_task",
            "schedule": 86400.0,  # Run daily (retention window, default 90 days)
        },
    },
)
