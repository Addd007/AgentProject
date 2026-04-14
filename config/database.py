"""数据库配置文件：仅支持 PostgreSQL。"""

import os


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

DB_TYPE = "postgresql"
_database_url = os.getenv("DATABASE_URL")
if _database_url:
    SQLALCHEMY_DATABASE_URL = _database_url
else:
    db_user = os.getenv("DB_USER", "postgres")
    db_password = _required_env("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "agent_db")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

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
METRICS_AUTH_TOKEN = os.getenv("METRICS_AUTH_TOKEN", "")
