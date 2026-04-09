#!/usr/bin/env python
"""
数据库初始化脚本：创建表结构和索引
"""

import sys
from utils.logger_handler import get_logger

logger = get_logger(__name__)

def init_db():
    """初始化数据库"""
    try:
        from utils.session_storage import SessionRecord, get_storage_backend, Base, SQLALCHEMY_AVAILABLE
        from utils.auth_service import Base as AuthBase
        from config.database import SQLALCHEMY_DATABASE_URL
        
        if not SQLALCHEMY_AVAILABLE:
            logger.error("SQLAlchemy is not installed")
            return False
        
        logger.info(f"Initializing database: {SQLALCHEMY_DATABASE_URL}")
        
        from sqlalchemy import create_engine
        engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
        
        Base.metadata.create_all(engine)
        AuthBase.metadata.create_all(engine)
        logger.info("Database initialized successfully")
        
        # 测试连接
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database connection test passed")
        
        return True
    except Exception as e:
        logger.exception(f"Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)
