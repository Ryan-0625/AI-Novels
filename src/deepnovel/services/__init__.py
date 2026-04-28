"""
系统服务模块

@file: services/__init__.py
@date: 2026-03-18
@version: 1.0
@description: 系统服务模块初始化
"""

from src.deepnovel.services.health_service import get_health_service, HealthService

__all__ = ["get_health_service", "HealthService"]
