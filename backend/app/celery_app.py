"""
Celery 异步任务配置
用于 AI 审查等耗时任务
"""
from celery import Celery
from app.core.config import settings

# Celery 应用实例
celery_app = Celery(
    "contract_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.celery_tasks.ai_review_tasks",
        "app.celery_tasks.notification_tasks",
        "app.celery_tasks.archive_tasks",
    ],
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_concurrency=4,
    # 路由配置
    task_routes={
        "app.celery_tasks.ai_review_tasks.*": {"queue": "ai_review"},
        "app.celery_tasks.notification_tasks.*": {"queue": "notifications"},
        "app.celery_tasks.archive_tasks.*": {"queue": "archive"},
    },
    # 重试配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
)

if settings.DEBUG:
    celery_app.conf.update(
        worker_log_format="%(asctime)s %(levelname)s %(message)s",
        worker_task_log_format="%(asctime)s %(levelname)s [%(task_name)s(%(task_id)s)] %(message)s",
    )
