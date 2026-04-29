"""
世界模拟 Agent 工具

Agent 可直接调用的世界模拟工具集：
- WorldStateTool: 世界状态机
- CharacterMindTool: 角色心智
- CausalReasoningTool: 因果推理
- NarrativeRecordTool: 叙事记录
- MemoryEncodingTool: 记忆编码
- MemoryRetrievalTool: 记忆检索
- MemoryConsolidationTool: 记忆巩固

@file: agents/tools/__init__.py
@date: 2026-04-29
"""

from .world_state_tool import WorldStateTool
from .character_mind_tool import CharacterMindTool
from .causal_reasoning_tool import CausalReasoningTool
from .narrative_record_tool import NarrativeRecordTool
from .memory_tools import (
    MemoryEncodingTool,
    MemoryRetrievalTool,
    MemoryConsolidationTool,
)
from .rag_tools import (
    DocumentIndexTool,
    DocumentRetrieveTool,
    KnowledgeBaseTool,
)

__all__ = [
    "WorldStateTool",
    "CharacterMindTool",
    "CausalReasoningTool",
    "NarrativeRecordTool",
    # 记忆系统工具
    "MemoryEncodingTool",
    "MemoryRetrievalTool",
    "MemoryConsolidationTool",
    # RAG 工具
    "DocumentIndexTool",
    "DocumentRetrieveTool",
    "KnowledgeBaseTool",
]
