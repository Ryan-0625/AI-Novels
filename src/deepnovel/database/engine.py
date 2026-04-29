"""
PostgreSQL 数据库引擎配置

使用 SQLModel (SQLAlchemy 2.0) + asyncpg 提供异步数据库访问。

@file: database/engine.py
@date: 2026-04-29
"""

import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# 默认连接URL，可通过环境变量覆盖
DEFAULT_DATABASE_URL = "postgresql+asyncpg://deepnovel:deepnovel_pass@localhost:5432/deepnovel"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
# 确保使用异步驱动
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,
    pool_recycle=300,
)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db():
    """初始化数据库 — 创建所有表"""
    # 延迟导入模型以确保表注册
    from deepnovel.models import novel, chapter, narrative, task  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()


@asynccontextmanager
async def get_session():
    """获取数据库会话的上下文管理器"""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db():
    """FastAPI依赖注入用的数据库会话生成器"""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
