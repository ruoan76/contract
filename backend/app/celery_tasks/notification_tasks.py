"""
通知任务模块
"""
import logging

from app.celery_tasks import celery_app
from app.utils.feishu import send_feishu_webhook_sync

logger = logging.getLogger(__name__)


@celery_app.task(name="notification.send_approval_reminder")
def send_approval_reminder(
    flow_id: int,
    step_id: int,
    approver_id: int,
) -> None:
    """
    发送审批提醒通知（飞书 webhook + 日志）
    """
    message = (
        f"审批流程 #{flow_id} 步骤 #{step_id} 待处理，"
        f"审批人 user_id={approver_id}"
    )
    send_feishu_webhook_sync(message, title="审批提醒")
    logger.info(
        "Sending approval reminder to user %s for flow %s step %s",
        approver_id,
        flow_id,
        step_id,
    )


@celery_app.task(name="notification.send_contract_signed")
def send_contract_signed(
    contract_id: int,
    user_id: int,
) -> None:
    """
    发送合同签署完成通知
    
    Args:
        contract_id: 合同ID
        user_id: 用户ID
    """
    # TODO: 实际发送通知
    logger.info(f"Sending contract signed notification to user {user_id} for contract {contract_id}")
    pass
