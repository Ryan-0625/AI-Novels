"""
服务层 — 业务逻辑封装

@file: services/__init__.py
@date: 2026-04-29
"""

from .base import BaseService
from .health_service import get_health_service, HealthService
from .novel_service import NovelService
from .task_service import TaskService

__all__ = [
    "BaseService",
    "get_health_service",
    "HealthService",
    "NovelService",
    "TaskService",
]
