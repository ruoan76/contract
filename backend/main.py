"""
合同审批管理平台 - 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1 import (
    contracts,
    approvals,
    counterparties,
    reviews,
    config as config_api,
    notifications,
    ai_review,
    ai_review_seeds,
    ai_review_demo,
    risks,
    seals,
    archives,
    audit,
    statistics,
    system,
    templates,
    clause_compare,
)
from app.utils.exceptions import register_exception_handlers
from app.middleware.auth_middleware import setup_auth_middleware
from app.middleware.audit_middleware import setup_audit_middleware
from app.middleware.logging_middleware import setup_logging_middleware
from app.celery_app import celery_app

try:
    from app.db.database import engine  # noqa: F401
    from app.db.base import Base  # noqa: F401
except ImportError:
    engine = None
    Base = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    print(f"🚀 合同审批平台启动 - 环境: {settings.ENVIRONMENT}")
    print(f"📊 数据库: {settings.DATABASE_URL}")
    print(f"🤖 AI 模型: {settings.AI_MODEL}")

    # 创建数据库表
    if engine is not None and Base is not None:
        try:
            print("📦 创建数据库表...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("✅ 数据库表创建完成")
        except Exception as e:
            print(f"⚠️  数据库表创建失败: {e}")

    if settings.CELERY_BROKER_URL:
        print("🔄 Celery beat scheduler 配置已启用")
        print("   注意: Celery beat 应该作为独立进程运行:")
        print("   celery -A app.celery_app beat")
    else:
        print("⚠️  Celery broker 未配置，跳过 Celery beat 启动")

    yield

    # 关闭时
    print("👋 合同审批平台关闭")
    if engine is not None:
        await engine.dispose()
        print("🔌 数据库连接已关闭")


app = FastAPI(
    title="合同审批管理平台",
    description="全生命周期数字化合同审批管理平台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册中间件 (注意顺序: logging -> audit -> auth)
setup_logging_middleware(app)
setup_audit_middleware(app)
setup_auth_middleware(app)

# 注册异常处理器
register_exception_handlers(app)

# 路由注册
app.include_router(contracts.router, prefix="/api/v1/contracts", tags=["合同管理"])
app.include_router(counterparties.router, prefix="/api/v1/counterparties", tags=["相对方管理"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["审批流程"])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["评审管理"])
app.include_router(config_api.router, prefix="/api/v1/config", tags=["系统配置"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["通知中心"])
app.include_router(ai_review.router, prefix="/api/v1/ai-review", tags=["AI 审查"])
app.include_router(ai_review_seeds.router, prefix="/api/v1/ai-review", tags=["AI 审查-种子"])
app.include_router(ai_review_demo.router, prefix="/api/v1/ai-review", tags=["AI 审查-演示"])
app.include_router(risks.router, prefix="/api/v1/risks", tags=["风险预警"])
app.include_router(seals.router, prefix="/api/v1/seals", tags=["用印管理"])
app.include_router(archives.router, prefix="/api/v1/archives", tags=["归档台账"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["审计日志"])
app.include_router(statistics.router, prefix="/api/v1/statistics", tags=["数据统计"])
app.include_router(system.router, prefix="/api/v1/system", tags=["系统管理"])
app.include_router(templates.router, prefix="/api/v1/templates", tags=["模板管理"])
app.include_router(clause_compare.router, prefix="/api/v1/clause-compare", tags=["条款比对"])


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
