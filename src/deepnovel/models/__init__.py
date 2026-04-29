"""
AI-Novels SQLModel 实体模型

从 dataclass 迁移到 SQLModel，提供数据库持久化能力。
保留向后兼容：旧代码可通过 .to_dict() 访问。

@file: models/__init__.py
@date: 2026-04-29
@version: 2.0.0
"""

from .novel import Novel, Character, WorldEntity, OutlineNode
from .chapter import ChapterOutline, ChapterContent
from .narrative import Conflict, NarrativeHook
from .task import Task, TaskStatus

__all__ = [
    "Novel",
    "Character",
    "WorldEntity",
    "OutlineNode",
    "ChapterOutline",
    "ChapterContent",
    "Conflict",
    "NarrativeHook",
    "Task",
    "TaskStatus",
]
