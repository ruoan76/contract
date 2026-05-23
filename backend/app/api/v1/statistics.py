"""
数据统计 API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.utils.auth import get_current_user

router = APIRouter()


def _month_bucket_expr(dialect_name: str, column):
    """按数据库方言生成月份聚合表达式。"""
    if dialect_name == "sqlite":
        return func.strftime("%Y-%m", column)
    if dialect_name in ("mysql", "mariadb"):
        return func.date_format(column, "%Y-%m")
    return func.date_trunc("month", column)


@router.get("/contracts", summary="合同统计")
async def get_contract_statistics(
    period: str = Query("month", description="month | quarter | year"),
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取合同统计数据"""
    from app.models.contract import Contract
    
    current_year = year or datetime.now().year
    
    # 按类型统计
    result = await db.execute(
        select(
            Contract.contract_type,
            func.count(),
            func.sum(Contract.amount),
            func.avg(Contract.amount),
        )
        .group_by(Contract.contract_type)
    )
    by_type = [
        {
            "type": row[0],
            "count": row[1],
            "amount": float(row[2] or 0),
            "avg_amount": float(row[3] or 0),
        }
        for row in result.all()
    ]
    
    # 按状态统计
    result = await db.execute(
        select(Contract.status, func.count())
        .group_by(Contract.status)
    )
    by_status = {row[0]: row[1] for row in result.all()}
    
    # 按风险等级统计
    result = await db.execute(
        select(Contract.risk_level, func.count())
        .group_by(Contract.risk_level)
    )
    by_risk = {row[0]: row[1] for row in result.all()}
    
    # 总数和总金额
    result = await db.execute(
        select(func.count(), func.sum(Contract.amount))
    )
    row = result.first()
    total_count = row[0]
    total_amount = float(row[1] or 0)
    
    return {
        "code": 200,
        "data": {
            "total_contracts": total_count,
            "total_amount": total_amount,
            "by_type": by_type,
            "by_status": by_status,
            "by_risk_level": by_risk,
        }
    }


@router.get("/approval-efficiency", summary="审批效率")
async def get_approval_efficiency(
    period: str = Query("month"),
    db: AsyncSession = Depends(get_db),
):
    """获取审批效率统计"""
    from app.models.contract import ApprovalFlow, Contract
    
    # 基础统计
    result = await db.execute(
        select(
            func.count(),
            func.avg(ApprovalFlow.duration_hours),
            func.max(ApprovalFlow.duration_hours),
            func.min(ApprovalFlow.duration_hours),
        )
        .where(ApprovalFlow.status == "approved")
    )
    row = result.first()
    
    total_flows = row[0] or 0
    avg_hours = float(row[1] or 0)
    max_hours = float(row[2] or 0)
    min_hours = float(row[3] or 0)
    
    # 超时统计
    if total_flows > 0:
        result = await db.execute(
            select(func.count())
            .where(ApprovalFlow.status == "approved")
            .where(ApprovalFlow.duration_hours > 48)
        )
        overtime_count = result.scalar() or 0
        overtime_rate = overtime_count / total_flows
    else:
        overtime_rate = 0.0
    
    # 找出瓶颈节点
    result = await db.execute(
        select(
            ApprovalFlow.current_node_id,
            func.avg(ApprovalFlow.duration_hours).label("avg_hours"),
            func.count().label("count"),
        )
        .where(ApprovalFlow.status == "approved")
        .where(ApprovalFlow.duration_hours > 0)
        .group_by(ApprovalFlow.current_node_id)
        .order_by(func.avg(ApprovalFlow.duration_hours).desc())
        .limit(5)
    )
    bottleneck_nodes = [
        {
            "node_name": row[0],
            "avg_hours": round(float(row[1] or 0), 2),
            "count": row[2],
        }
        for row in result.all()
    ]
    
    return {
        "code": 200,
        "data": {
            "total_flows": total_flows,
            "avg_approval_hours": round(avg_hours, 2),
            "max_approval_hours": round(max_hours, 2),
            "min_approval_hours": round(min_hours, 2),
            "overtime_rate": round(overtime_rate, 4),
            "bottleneck_nodes": bottleneck_nodes,
        }
    }


@router.get("/risk-trend", summary="风险趋势")
async def get_risk_trend(
    period: str = Query("month"),
    db: AsyncSession = Depends(get_db),
):
    """获取风险趋势统计"""
    from app.models.contract import RiskAlert
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    dialect_name = db.bind.dialect.name if db.bind else "sqlite"
    month_expr = _month_bucket_expr(dialect_name, RiskAlert.created_at)
    
    result = await db.execute(
        select(
            month_expr.label("month"),
            RiskAlert.alert_level,
            func.count().label("count"),
        )
        .where(RiskAlert.created_at >= start_date)
        .where(RiskAlert.created_at <= end_date)
        .group_by(month_expr, RiskAlert.alert_level)
        .order_by("month", RiskAlert.alert_level)
    )
    
    trend_data = {}
    for row in result.all():
        month = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
        level = row[1]
        count = row[2]
        
        if month not in trend_data:
            trend_data[month] = {"month": month, "high": 0, "medium": 0, "low": 0}
        
        if level == "high":
            trend_data[month]["high"] += count
        elif level == "medium":
            trend_data[month]["medium"] += count
        elif level == "low":
            trend_data[month]["low"] += count
    
    trend_list = sorted(trend_data.values(), key=lambda x: x["month"])[-6:]
    
    return {
        "code": 200,
        "data": {
            "period": period,
            "trend": trend_list,
        }
    }
