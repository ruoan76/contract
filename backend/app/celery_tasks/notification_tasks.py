"""
通知任务模块
"""
import logging

from app.celery_tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="notification.send_approval_reminder")
def send_approval_reminder(
    flow_id: int,
    step_id: int,
    approver_id: int,
) -> None:
    """
    发送审批提醒通知
    
    Args:
        flow_id: 审批流程ID
        step_id: 审批步骤ID
        approver_id: 审批人ID
    """
    # TODO: 实际发送通知（邮件/短信/站内信）
    logger.info(f"Sending approval reminder to user {approver_id} for flow {flow_id}")
    pass


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
