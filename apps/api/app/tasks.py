"""Celery tasks. Real jobs arrive in Prompt 4; this is the connectivity check."""

from app.celery_app import celery_app


@celery_app.task(name="gapscout.ping")
def ping() -> str:
    return "pong"
