"""会话存储层：基于 PostgreSQL，提供统一接口。"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from abc import ABC, abstractmethod

from utils.logger_handler import get_logger

try:
    from sqlalchemy import create_engine, Column, String, JSON, DateTime, Index
    from sqlalchemy.orm import Session, declarative_base, sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

logger = get_logger(__name__)

Base = declarative_base() if SQLALCHEMY_AVAILABLE else None


class SessionRecord(Base if SQLALCHEMY_AVAILABLE else object):
    """数据库表模型"""
    if SQLALCHEMY_AVAILABLE:
        __tablename__ = "sessions"

        session_id = Column(String(36), primary_key=True, index=True)
        user_id = Column(String(50), index=True)
        messages = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow, index=True)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        status = Column(String(20), default="active")
        expires_at = Column(DateTime, nullable=True)

        __table_args__ = (
            Index("idx_user_id_updated_at", "user_id", "updated_at"),
            Index("idx_status_expires", "status", "expires_at"),
        )


class SessionStorageBackend(ABC):
    """存储后端抽象类"""

    @abstractmethod
    def load_all_active(self, max_days: int = 7) -> Dict[str, list]:
        """加载所有活跃会话"""
        pass

    @abstractmethod
    def load_all_active_with_users(self, max_days: int = 7) -> Dict[str, Dict[str, Any]]:
        """加载所有活跃会话及所属用户"""
        pass

    @abstractmethod
    def save_session(self, session_id: str, messages: list, user_id: str) -> bool:
        """保存单个会话"""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        pass

    @abstractmethod
    def archive_expired_sessions(self, days: int = 30) -> int:
        """归档过期会话，返回归档数量"""
        pass

    @abstractmethod
    def cleanup_archived(self, days: int = 90) -> int:
        """清理已归档的会话，返回删除数量"""
        pass


class SqlAlchemyBackend(SessionStorageBackend):
    """SQLAlchemy 后端（PostgreSQL）"""

    def __init__(self, db_url: str):
        if not SQLALCHEMY_AVAILABLE:
            raise RuntimeError("SQLAlchemy is required for database backend")

        self.engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        logger.info(f"Initialized session storage with {db_url}")

    def load_all_active(self, max_days: int = 7) -> Dict[str, list]:
        """从数据库加载近期活跃会话"""
        try:
            db = self.SessionLocal()
            cutoff = datetime.utcnow() - timedelta(days=max_days)
            records = db.query(SessionRecord).filter(
                SessionRecord.status == "active",
                SessionRecord.updated_at >= cutoff,
            ).all()

            result = {}
            for record in records:
                try:
                    result[record.session_id] = json.loads(
                        json.dumps(record.messages)
                    ) if isinstance(record.messages, str) else record.messages
                except Exception as e:
                    logger.warning(f"Failed to load session {record.session_id}: {e}")

            db.close()
            logger.info(f"Loaded {len(result)} active sessions")
            return result
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            return {}

    def load_all_active_with_users(self, max_days: int = 7) -> Dict[str, Dict[str, Any]]:
        try:
            db = self.SessionLocal()
            cutoff = datetime.utcnow() - timedelta(days=max_days)
            records = db.query(SessionRecord).filter(
                SessionRecord.status == "active",
                SessionRecord.updated_at >= cutoff,
            ).all()

            result: Dict[str, Dict[str, Any]] = {}
            for record in records:
                messages = json.loads(json.dumps(record.messages)) if isinstance(record.messages, str) else record.messages
                result[record.session_id] = {
                    "messages": messages,
                    "user_id": record.user_id or "anonymous",
                }

            db.close()
            return result
        except Exception as e:
            logger.error(f"Failed to load session metadata: {e}")
            return {}

    def save_session(self, session_id: str, messages: list, user_id: str = "default") -> bool:
        """保存会话到数据库"""
        try:
            db = self.SessionLocal()
            record = db.query(SessionRecord).filter(
                SessionRecord.session_id == session_id
            ).first()

            now = datetime.utcnow()
            if record:
                record.messages = messages
                record.updated_at = now
                record.user_id = user_id
            else:
                record = SessionRecord(
                    session_id=session_id,
                    user_id=user_id,
                    messages=messages,
                    created_at=now,
                    updated_at=now,
                    status="active",
                )
                db.add(record)

            db.commit()
            db.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """软删除会话"""
        try:
            db = self.SessionLocal()
            record = db.query(SessionRecord).filter(
                SessionRecord.session_id == session_id
            ).first()

            if record:
                record.status = "deleted"
                record.updated_at = datetime.utcnow()
                db.commit()
            db.close()
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def archive_expired_sessions(self, days: int = 30) -> int:
        """归档过期会话"""
        try:
            db = self.SessionLocal()
            cutoff = datetime.utcnow() - timedelta(days=days)
            count = db.query(SessionRecord).filter(
                SessionRecord.status == "active",
                SessionRecord.updated_at < cutoff,
            ).update({"status": "archived"})

            db.commit()
            db.close()
            logger.info(f"Archived {count} expired sessions")
            return count
        except Exception as e:
            logger.error(f"Failed to archive sessions: {e}")
            return 0

    def cleanup_archived(self, days: int = 90) -> int:
        """清理已归档的会话"""
        try:
            db = self.SessionLocal()
            cutoff = datetime.utcnow() - timedelta(days=days)
            count = db.query(SessionRecord).filter(
                SessionRecord.status == "deleted",
                SessionRecord.updated_at < cutoff,
            ).delete()

            db.commit()
            db.close()
            logger.info(f"Deleted {count} archived sessions")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup archived sessions: {e}")
            return 0


class MemoryBackend(SessionStorageBackend):
    """纯内存后端（开发测试用）"""

    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}

    def load_all_active(self, max_days: int = 7) -> Dict[str, list]:
        return {
            sid: v["messages"]
            for sid, v in self.data.items()
            if v.get("status") == "active"
        }

    def load_all_active_with_users(self, max_days: int = 7) -> Dict[str, Dict[str, Any]]:
        return {
            sid: {"messages": v["messages"], "user_id": v.get("user_id", "anonymous")}
            for sid, v in self.data.items()
            if v.get("status") == "active"
        }

    def save_session(self, session_id: str, messages: list, user_id: str = "default") -> bool:
        self.data[session_id] = {
            "messages": messages,
            "user_id": user_id,
            "updated_at": datetime.utcnow(),
            "status": "active",
        }
        return True

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.data:
            self.data[session_id]["status"] = "deleted"
        return True

    def archive_expired_sessions(self, days: int = 30) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = 0
        for v in self.data.values():
            if v.get("status") == "active" and v.get("updated_at", datetime.utcnow()) < cutoff:
                v["status"] = "archived"
                count += 1
        return count

    def cleanup_archived(self, days: int = 90) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        to_delete = [
            sid for sid, v in self.data.items()
            if v.get("status") == "deleted" and v.get("updated_at", datetime.utcnow()) < cutoff
        ]
        for sid in to_delete:
            del self.data[sid]
        return len(to_delete)


def get_storage_backend(use_db: bool = True) -> SessionStorageBackend:
    """工厂函数：获取存储后端"""
    if not use_db or not SQLALCHEMY_AVAILABLE:
        logger.warning("Using in-memory backend (sessions will not persist on restart)")
        return MemoryBackend()

    from config.database import SQLALCHEMY_DATABASE_URL
    try:
        return SqlAlchemyBackend(SQLALCHEMY_DATABASE_URL)
    except Exception as e:
        logger.error(f"Failed to initialize database backend: {e}, falling back to memory")
        return MemoryBackend()
