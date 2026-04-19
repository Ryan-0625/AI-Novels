"""
DeepNovel - AI-powered novel generation framework

@file: __init__.py
@date: 2026-03-12
@version: 1.0
@description: Main package initialization
"""

__version__ = "1.0.0"
__author__ = "AI-Novels Team"

# Import main components
from src.deepnovel.agents.base import BaseAgent, AgentConfig, AgentState, MessageType, Message
from src.deepnovel.utils import log_info, log_warn, log_error, log_debug
from src.deepnovel.services.health_service import get_health_service, HealthService

__all__ = [
    "BaseAgent",
    "AgentConfig",
    "AgentState",
    "MessageType",
    "Message",
    "log_info",
    "log_warn",
    "log_error",
    "log_debug",
    "get_health_service",
    "HealthService",
]
