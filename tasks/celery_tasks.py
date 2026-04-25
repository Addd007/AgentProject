
# Celery 配置和异步任务定义

import sys
import time
from datetime import datetime, timedelta
from celery import Celery
from celery.schedules import crontab
from prometheus_client import start_http_server
from config.database import CELERY_BROKER, CELERY_BACKEND, CELERY_METRICS_PORT, ENABLE_METRICS
from utils.logger_handler import get_logger
from utils.metrics import record_celery_task, session_archived
from rag.user_memory import UserMemoryService

import sys
import time
from datetime import datetime, timedelta
from celery import Celery
from celery.schedules import crontab
from prometheus_client import start_http_server
from config.database import CELERY_BROKER, CELERY_BACKEND, CELERY_METRICS_PORT, ENABLE_METRICS
from utils.logger_handler import get_logger
from utils.metrics import record_celery_task, session_archived
from rag.user_memory import UserMemoryService

logger = get_logger(__name__)

def _maybe_start_celery_metrics_server() -> None:
    if not ENABLE_METRICS:
        return
    if "worker" not in sys.argv:
        return
    try:
        start_http_server(CELERY_METRICS_PORT, addr="0.0.0.0")
        logger.info("Celery metrics server started on port %s", CELERY_METRICS_PORT)
    except OSError as exc:
        logger.warning("Failed to start Celery metrics server on port %s: %s", CELERY_METRICS_PORT, exc)


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
)

_maybe_start_celery_metrics_server()

ALL_BEAT_SCHEDULE = {
    "archive-expired-sessions": {
        "task": "tasks.celery_tasks.archive_expired_sessions_task",
        "schedule": crontab(hour=2, minute=0),
    },
    "cleanup-deleted-sessions": {
        "task": "tasks.celery_tasks.cleanup_deleted_sessions_task",
        "schedule": crontab(hour=3, minute=0),
    },
    "backup-sessions": {
        "task": "tasks.celery_tasks.backup_sessions_task",
        "schedule": crontab(hour=4, minute=0),
    },
    "compress-user-memory-task": {
        "task": "tasks.celery_tasks.compress_user_memory_task",
        "schedule": crontab(hour=1, minute=0),
        "args": ("default", 180),  # 可按需遍历所有user_id
    },
    "archive-cold-memory-task": {
        "task": "tasks.celery_tasks.archive_cold_memory_task",
        "schedule": crontab(hour=5, minute=0),
        "args": (365,),
    },
}
celery_app.conf.beat_schedule = ALL_BEAT_SCHEDULE

@celery_app.task
def compress_user_memory_task(user_id: str, days: int = 180):
    """
    定期压缩用户长期记忆：将days天前的记忆合并为一条摘要，减少存储压力。
    """
    service = UserMemoryService()
    # 1. 拉取老记忆
    cutoff = datetime.utcnow() - timedelta(days=days)
    all_memories = service.retrieve(user_id=user_id, query="", k=1000, days=3650)
    old_memories = [m for m in all_memories if m.metadata.get("created_at") and datetime.fromisoformat(m.metadata["created_at"]) < cutoff]
    if not old_memories:
        return {"compressed": 0}
    # 2. 合并为摘要（调用 LLM 生成摘要）
    all_text = "\n".join([m.content for m in old_memories])
    try:
        from model.factory import get_chat_model
        llm = get_chat_model()
        prompt = f"请对以下用户历史对话和事实进行归纳总结，生成一段200字以内的摘要，突出用户偏好、行为和重要事件：\n{all_text[:4000]}"
        summary_text = llm.invoke(prompt)
        if isinstance(summary_text, dict) and "content" in summary_text:
            summary_text = summary_text["content"]
        summary_text = f"历史摘要（{days}天前）：\n" + (summary_text.strip() if summary_text else "")
    except Exception as e:
        # 回退到简单拼接
        summary_text = f"历史摘要（{days}天前）：\n" + all_text[:2000]
    # 3. 写回新摘要
    service.add_memory(user_id=user_id, text=summary_text, memory_type="fact", extra_metadata={"source": "compress", "compressed_until": cutoff.isoformat()})
    # 4. 删除老数据
    for m in old_memories:
        created_at = m.metadata.get("created_at")
        if created_at:
            try:
                service.vector_store.delete(where={"user_id": user_id, "created_at": created_at})
            except Exception:
                pass
    return {"compressed": len(old_memories)}

@celery_app.task
def archive_cold_memory_task(days: int = 365):
    """
    定期归档冷数据：将days天前的长期记忆导出到对象存储并从在线库删除。
    """
    service = UserMemoryService()
    cutoff = datetime.utcnow() - timedelta(days=days)
    # 遍历所有 user_id，假设有 user_id_list
    user_id_list = ["default"]  # TODO: 替换为实际所有用户ID列表
    total_archived = 0
    for user_id in user_id_list:
        all_memories = service.retrieve(user_id=user_id, query="", k=10000, days=3650)
        cold_memories = [m for m in all_memories if m.metadata.get("created_at") and datetime.fromisoformat(m.metadata["created_at"]) < cutoff]
        # 1. 导出到对象存储（伪代码，实际需实现save_to_oss）
        # save_to_oss(cold_memories)
        # 2. 删除冷数据
        for m in cold_memories:
            created_at = m.metadata.get("created_at")
            if created_at:
                try:
                    service.vector_store.delete(where={"user_id": user_id, "created_at": created_at})
                except Exception:
                    pass
        total_archived += len(cold_memories)
    return {"archived": total_archived}

"""
Celery 配置和异步任务定义
"""



logger = get_logger(__name__)


def _maybe_start_celery_metrics_server() -> None:
    if not ENABLE_METRICS:
        return
    if "worker" not in sys.argv:
        return

    try:
        start_http_server(CELERY_METRICS_PORT, addr="0.0.0.0")
        logger.info("Celery metrics server started on port %s", CELERY_METRICS_PORT)
    except OSError as exc:
        logger.warning("Failed to start Celery metrics server on port %s: %s", CELERY_METRICS_PORT, exc)







@celery_app.task(bind=True, max_retries=3)
def save_session_async(self, session_id: str, messages: list, user_id: str = "default"):
    """异步保存会话到数据库"""
    started_at = time.perf_counter()
    try:
        from utils.session_storage import get_storage_backend
        
        backend = get_storage_backend(use_db=True)
        success = backend.save_session(session_id, messages, user_id)
        
        if success:
            logger.info(f"Session {session_id} saved successfully")
            record_celery_task("save_session_async", "success", time.perf_counter() - started_at)
            return {"status": "success", "session_id": session_id}
        else:
            raise Exception("Failed to save session")
    except Exception as exc:
        logger.error(f"Failed to save session {session_id}: {exc}")
        retry_count = self.request.retries
        if retry_count < self.max_retries:
            record_celery_task("save_session_async", "retry", time.perf_counter() - started_at)
            raise self.retry(exc=exc, countdown=2 ** retry_count)
        else:
            logger.error(f"Max retries exceeded for session {session_id}")
            record_celery_task("save_session_async", "failed", time.perf_counter() - started_at)
            return {"status": "failed", "session_id": session_id, "error": str(exc)}


@celery_app.task
def archive_expired_sessions_task():
    """定时任务：归档过期会话"""
    started_at = time.perf_counter()
    try:
        from config.database import SESSION_EXPIRE_DAYS
        from utils.session_storage import get_storage_backend
        
        backend = get_storage_backend(use_db=True)
        count = backend.archive_expired_sessions(SESSION_EXPIRE_DAYS)
        logger.info(f"Archived {count} expired sessions")
        if count > 0:
            session_archived.inc(count)
        record_celery_task("archive_expired_sessions_task", "success", time.perf_counter() - started_at)
        return {"archived_count": count}
    except Exception as exc:
        logger.error(f"Failed to archive sessions: {exc}")
        record_celery_task("archive_expired_sessions_task", "failed", time.perf_counter() - started_at)
        return {"error": str(exc)}


@celery_app.task
def cleanup_deleted_sessions_task():
    """定时任务：清理已删除的会话"""
    started_at = time.perf_counter()
    try:
        from config.database import SESSION_ARCHIVE_DAYS
        from utils.session_storage import get_storage_backend
        
        backend = get_storage_backend(use_db=True)
        count = backend.cleanup_deleted_sessions(SESSION_ARCHIVE_DAYS)
        logger.info(f"Deleted {count} deleted sessions")
        record_celery_task("cleanup_deleted_sessions_task", "success", time.perf_counter() - started_at)
        return {"deleted_count": count}
    except Exception as exc:
        logger.error(f"Failed to cleanup deleted sessions: {exc}")
        record_celery_task("cleanup_deleted_sessions_task", "failed", time.perf_counter() - started_at)
        return {"error": str(exc)}


@celery_app.task
def backup_sessions_task():
    """定时任务：备份会话数据库"""
    started_at = time.perf_counter()
    try:
        import os
        import subprocess
        from datetime import datetime, timezone
        from config.database import BACKUP_DIR

        db_host = os.getenv("DB_HOST", "localhost")
        db_user = os.getenv("DB_USER", "postgres")
        db_name = os.getenv("DB_NAME", "agent_db")
        db_password = os.getenv("DB_PASSWORD")
        if not db_password:
            raise RuntimeError("Missing required environment variable: DB_PASSWORD")
        
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
        record_celery_task("backup_sessions_task", "success", time.perf_counter() - started_at)
        return {"backup_file": backup_file}
    except Exception as exc:
        logger.error(f"Failed to backup sessions: {exc}")
        record_celery_task("backup_sessions_task", "failed", time.perf_counter() - started_at)
        return {"error": str(exc)}
