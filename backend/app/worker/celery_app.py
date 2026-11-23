from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ideaform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=1800,
    task_soft_time_limit=1500,
    broker_connection_retry_on_startup=True,
    task_default_queue="ideaform",
)


@celery_app.task(name="ideaform.ping")
def ping() -> str:
    return "pong"
