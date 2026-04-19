"""
Agent模块初始化

@file: agents/__init__.py
@date: 2026-03-12
@author: AI-Novels Team
@version: 1.0
@description: 导出Agent模块的公共接口
"""

from .base import BaseAgent, AgentConfig, AgentState, MessageType
from .implementations import (
    CoordinatorAgent,
    TaskManagerAgent,
    ConfigEnhancerAgent,
    HealthCheckerAgent,
    OutlinePlannerAgent,
    ChapterSummaryAgent,
    CharacterGeneratorAgent,
    WorldBuilderAgent,
    HookGeneratorAgent,
    ConflictGeneratorAgent,
    ContentGeneratorAgent,
    QualityCheckerAgent,
    StorylineIntegratorAgent
)

__all__ = [
    'BaseAgent',
    'AgentConfig',
    'AgentState',
    'MessageType',
    'CoordinatorAgent',
    'TaskManagerAgent',
    'ConfigEnhancerAgent',
    'HealthCheckerAgent',
    'OutlinePlannerAgent',
    'ChapterSummaryAgent',
    'CharacterGeneratorAgent',
    'WorldBuilderAgent',
    'HookGeneratorAgent',
    'ConflictGeneratorAgent',
    'ContentGeneratorAgent',
    'QualityCheckerAgent',
    'StorylineIntegratorAgent'
]
