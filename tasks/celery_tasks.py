"""
Celery 配置和异步任务定义
"""

from celery import Celery
from celery.schedules import crontab
from config.database import CELERY_BROKER, CELERY_BACKEND
from utils.logger_handler import get_logger

logger = get_logger(__name__)

celery_app = Celery(
    __name__,
    broker=CELERY_BROKER,
    backend=CELERY_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    beat_schedule={  # 定时任务配置
        "archive-expired-sessions": { #归档过期会话
            "task": "tasks.celery_tasks.archive_expired_sessions_task",
            "schedule": crontab(hour=2, minute=0),
        },
        "cleanup-deleted-sessions": { #清理已删除的会话
            "task": "tasks.celery_tasks.cleanup_deleted_sessions_task",
            "schedule": crontab(hour=3, minute=0),
        },
        "backup-sessions": { #备份会话数据库
            "task": "tasks.celery_tasks.backup_sessions_task",
            "schedule": crontab(hour=4, minute=0),
        },
    },
)


@celery_app.task(bind=True, max_retries=3)
def save_session_async(self, session_id: str, messages: list, user_id: str = "default"):
    """异步保存会话到数据库"""
    try:
        from utils.session_storage import get_storage_backend
        
        backend = get_storage_backend(use_db=True)
        success = backend.save_session(session_id, messages, user_id)
        
        if success:
            logger.info(f"Session {session_id} saved successfully")
            return {"status": "success", "session_id": session_id}
        else:
            raise Exception("Failed to save session")
    except Exception as exc:
        logger.error(f"Failed to save session {session_id}: {exc}")
        retry_count = self.request.retries
        if retry_count < self.max_retries:
            raise self.retry(exc=exc, countdown=2 ** retry_count)
        else:
            logger.error(f"Max retries exceeded for session {session_id}")
            return {"status": "failed", "session_id": session_id, "error": str(exc)}


@celery_app.task
def archive_expired_sessions_task():
    """定时任务：归档过期会话"""
    try:
        from config.database import SESSION_EXPIRE_DAYS
        from utils.session_storage import get_storage_backend
        
        backend = get_storage_backend(use_db=True)
        count = backend.archive_expired_sessions(SESSION_EXPIRE_DAYS)
        logger.info(f"Archived {count} expired sessions")
        return {"archived_count": count}
    except Exception as exc:
        logger.error(f"Failed to archive sessions: {exc}")
        return {"error": str(exc)}


@celery_app.task
def cleanup_deleted_sessions_task():
    """定时任务：清理已删除的会话"""
    try:
        from config.database import SESSION_ARCHIVE_DAYS
        from utils.session_storage import get_storage_backend
        
        backend = get_storage_backend(use_db=True)
        count = backend.cleanup_deleted_sessions(SESSION_ARCHIVE_DAYS)
        logger.info(f"Deleted {count} deleted sessions")
        return {"deleted_count": count}
    except Exception as exc:
        logger.error(f"Failed to cleanup deleted sessions: {exc}")
        return {"error": str(exc)}


@celery_app.task
def backup_sessions_task():
    """定时任务：备份会话数据库"""
    try:
        import os
        import subprocess
        from datetime import datetime, timezone
        from config.database import BACKUP_DIR

        db_host = os.getenv("DB_HOST", "localhost")
        db_user = os.getenv("DB_USER", "postgres")
        db_name = os.getenv("DB_NAME", "agent_db")
        db_password = os.getenv("DB_PASSWORD", "password")
        
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"postgresql_backup_{timestamp}.sql")
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        with open(backup_file, "w", encoding="utf-8") as file_obj:
            subprocess.run(
                ["pg_dump", "-h", db_host, "-U", db_user, "-d", db_name],
                check=True,
                env=env,
                stdout=file_obj,
            )
        
        logger.info(f"Backup created at {backup_file}")
        return {"backup_file": backup_file}
    except Exception as exc:
        logger.error(f"Failed to backup sessions: {exc}")
        return {"error": str(exc)}
