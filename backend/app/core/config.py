"""
应用配置
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Optional

# 本地开发默认可写目录（避免 macOS /data 只读导致上传 500）
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_FILE_STORAGE_PATH = str(_BACKEND_ROOT / "data" / "contract-files")


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    APP_NAME: str = "合同审批管理平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 数据库配置
    DATABASE_URL: str = "mysql+asyncmy://root:password@localhost:3306/contract_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 小时
    
    # AI 配置（AI_BASE_URL 须与本机 mlx_lm.server 端口一致，见 backend/docs/mlx-local-dev.md）
    AI_MODEL: str = "mlx-community/Qwen3.6-35B-A3B-4bit"
    AI_REVIEW_MOCK: bool = True
    # Mock=0 时：True=API 进程内同步调 MLX（本地开发推荐）；False=走 Celery 异步
    AI_REVIEW_SYNC: bool = True
    AI_PARSE_MOCK: bool = True
    AI_BASE_URL: str = "http://127.0.0.1:27366/v1"
    AI_API_KEY: str = "local"
    AI_TEMPERATURE: float = 0.1
    AI_MAX_TOKENS: int = 4096
    AI_AUTO_REVIEW_ON_UPLOAD: bool = False
    AI_REVIEW_SELF_CORRECT: bool = True
    AI_REQUIRE_CONFIRM: bool = False
    AI_REQUEST_TIMEOUT: float = 120.0
    AI_REVIEW_SEGMENT_THRESHOLD: int = 12000
    AI_REVIEW_SEGMENT_SIZE: int = 10000
    AI_REVIEW_MAX_ISSUES_PER_DIM: int = 15
    AI_REVIEW_MAX_CONCURRENT: int = 2
    AI_RAG_MODE: str = "keyword"  # keyword | bm25 | chroma
    AI_RAG_BM25_MIN_SCORE: float = 1.5
    AI_PROMPT_VERSION: str = "pb-v1.0"
    AI_ALLOW_MOCK_IN_PROD: bool = False
    FILE_STORAGE: str = "local"  # local | minio
    FILE_STORAGE_PATH: str = _DEFAULT_FILE_STORAGE_PATH
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = ["pdf", "doc", "docx", "jpg", "png"]
    # 扫描 PDF OCR（EasyOCR）
    AI_OCR_ENABLED: bool = True
    AI_OCR_MIN_CHARS: int = 200
    AI_OCR_MAX_PAGES: int = 40
    CONTRACT_CONTENT_MAX_CHARS: int = 500_000
    
    # MinIO 配置（可选）
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "contract-files"
    
    # Celery 配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # CORS 配置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
    ]
    
    # 安全配置
    BCRYPT_ROUNDS: int = 12
    PASSWORD_MIN_LENGTH: int = 8
    
    # 审批配置
    DEFAULT_APPROVAL_TIMEOUT_HOURS: int = 24
    AUTO_APPROVE_ENABLED: bool = False

    # 飞书 Webhook（可选，配置后推送审批/评审通知）
    FEISHU_WEBHOOK_URL: Optional[str] = None
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/data/logs/contract.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
