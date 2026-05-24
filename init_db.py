import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# Import all models to register them in metadata
from ai_novels.models.task import Task
from ai_novels.models.novel import Novel
from ai_novels.models.chapter import ChapterContent, ChapterOutline

async def init():
    url = "postgresql+asyncpg://ai_novels:ai_novels_pass@localhost:5432/ai_novels"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Database tables created successfully")

if __name__ == "__main__":
    asyncio.run(init())
