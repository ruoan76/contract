"""
Celery 任务模块
包含 AI 审查、通知等异步任务
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
    ],
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    task_track_started=True,
    result_expiry=3600,
)


# 自定义 Celery Base Task
class TaskBase(celery_app.Task):
    """自定义 Celery 任务基类"""
    pass
