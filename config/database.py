"""数据库配置文件：仅支持 PostgreSQL。"""

import os

DB_TYPE = "postgresql"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
    f"{os.getenv('DB_PASSWORD', 'password')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:"
    f"{os.getenv('DB_PORT', '5432')}/"
    f"{os.getenv('DB_NAME', 'agent_db')}"
)

DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
SQLALCHEMY_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
SQLALCHEMY_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "40"))
SQLALCHEMY_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

ENABLE_ASYNC = os.getenv("ENABLE_ASYNC", "false").lower() == "true"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER = os.getenv("CELERY_BROKER", REDIS_URL)
CELERY_BACKEND = os.getenv("CELERY_BACKEND", REDIS_URL)

SESSION_EXPIRE_DAYS = int(os.getenv("SESSION_EXPIRE_DAYS", "30"))
SESSION_ARCHIVE_DAYS = int(os.getenv("SESSION_ARCHIVE_DAYS", "90"))

BACKUP_DIR = os.getenv("BACKUP_DIR", "./backups")
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
METRICS_PORT = int(os.getenv("METRICS_PORT", "8001"))
CELERY_METRICS_PORT = int(os.getenv("CELERY_METRICS_PORT", "8002"))
