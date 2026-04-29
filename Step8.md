# Step 8: 工具层重构 - MCP兼容的统一工具架构

> 版本: 1.0
> 日期: 2026-04-28
> 依赖: Step1-7
> 目标: 构建面向Agent的、MCP兼容的、可发现/可编排的统一工具层

---

## 1. 设计哲学

### 1.1 核心转变

```
从：硬编码工具方法（BaseAgent._execute_tool）     → 到：装饰器注册 + 动态发现
从：字符串列表声明能力（AgentConfig.tools=[]）    → 到：结构化工具Schema + 权限系统
从：同步阻塞工具调用                            → 到：异步执行 + 并发控制 + 超时管理
从：工具与Agent紧耦合                          → 到：工具即服务（Tool as a Service）
从：零Embedding实现                            → 到：多引擎Embedding工具链
从：无LLM函数调用支持                          → 到：自动JSON Schema生成 + Function Calling
```

### 1.2 设计原则

1. **工具即能力边界**：Agent能做什么 = 它能调用的工具集，工具即权限
2. **声明即契约**：`@tool`装饰器同时定义实现、Schema、权限、文档
3. **MCP即标准**：工具定义遵循Model Context Protocol，兼容OpenAI/Claude/通义等主流平台
4. **发现即注册**：工具自动注册到Registry，Agent启动时动态发现可用工具
5. **执行即观测**：每次工具调用自动记录日志、性能指标、调用链路
6. **Embedding即基础**：文本向量化是工具层的一等公民，所有RAG/记忆/检索工具依赖它

### 1.3 行业前沿参考

| 来源 | 核心借鉴 | 适用场景 |
|------|---------|---------|
| **MCP (Model Context Protocol)** (2024) | 标准化工具定义、上下文传输、服务端发现 | 跨平台Agent工具兼容性 |
| **OpenAI Function Calling** (2024) | JSON Schema参数定义、结构化输出 | LLM驱动的工具调用 |
| **LangChain Tools** (2024) | `@tool`装饰器、工具链组合、回调系统 | 快速工具开发 |
| **CrewAI Tools** (2024) | Agent专属工具集、权限隔离 | 多Agent协作场景 |
| **Semantic Kernel** (Microsoft) | 原生函数、插件系统、Planner | 企业级AI编排 |
| **Vercel AI SDK** (2024) | 流式工具调用、前端集成 | 实时交互应用 |
| **Haystack Tools** (2024) | 组件化工具、Pipeline编排 | RAG流水线 |

---

## 2. 现状诊断

### 2.1 当前组件清单

| 组件 | 文件 | 问题 | 严重程度 |
|------|------|------|---------|
| `BaseAgent._execute_tool()` | `agents/base.py:376` | 硬编码8个工具，数据库工具全部`implemented=False` | **严重** |
| `AgentConfig.tools` | `agents/base.py:90` | `List[str]`纯字符串列表，无Schema、无验证 | **严重** |
| `EmbeddingClient` | `llm/base.py:103` | **零实现** — 所有适配器均未实现embed/embed_batch | **致命** |
| `execute_tool()`调用 | 全代码库搜索 | **零处调用** — 工具系统从未被使用 | **致命** |
| ToolRegistry | 不存在 | 无工具注册中心，无发现机制 | **严重** |
| `@tool`装饰器 | 不存在 | 无声明式工具定义方式 | **中** |
| JSON Schema生成 | 不存在 | LLM无法自动了解工具参数格式 | **严重** |
| 工具权限系统 | 不存在 | Agent可调用任何工具，无能力边界 | **中** |
| 工具执行监控 | 不存在 | 无调用日志、无性能指标、无错误追踪 | **中** |
| 异步工具执行 | 不存在 | 所有工具同步阻塞，无并发控制 | **中** |
| MCP兼容层 | 不存在 | 无法与外部Agent框架互通 | **低** |

### 2.2 核心问题总结

```
当前状态：有工具的"影子"，没有工具的"实体"

1. 工具定义与实现混杂在BaseAgent中        → 违反单一职责原则
2. Agent配置只是字符串列表                 → 无类型安全，LLM无法理解参数
3. EmbeddingClient是抽象幽灵               → RAG/记忆/检索全部无法工作
4. 零处工具调用                            → 整个工具系统是无用代码
5. 无工具注册中心                          → 新增工具需手动修改多处
6. 无LLM函数调用Schema                     → Agent无法让LLM自主选择工具
7. 无工具执行隔离                          → 工具崩溃会拖垮Agent
8. 无执行观测                              → 无法追踪工具调用链、无法调试
```

### 2.3 Steps 1-7 工具需求汇总

| 来源步骤 | 所需工具类别 | 具体工具示例 | 紧急程度 |
|---------|------------|------------|---------|
| **Step1** 数据层 | 世界模拟工具 | `fact_set`, `fact_query`, `entity_create`, `causal_trace`, `mind_simulate` | 高 |
| **Step2** 记忆系统 | 记忆管理工具 | `memory_store`, `memory_retrieve`, `memory_consolidate`, `attention_focus` | 高 |
| **Step3** LLM层 | 生成/嵌入工具 | `llm_generate`, `llm_embed`, `llm_stream`, `model_info` | 高 |
| **Step4** Agent层 | Agent协作工具 | `agent_message`, `agent_handoff`, `state_read`, `state_write` | 中 |
| **Step5** 任务调度 | 工作流工具 | `workflow_create`, `task_submit`, `task_status`, `checkpoint_save` | 中 |
| **Step6** RAG检索 | 检索增强工具 | `retrieve_world`, `retrieve_character`, `retrieve_style`, `query_transform` | 高 |
| **Step7** 配置系统 | 配置管理工具 | `config_validate`, `config_compose`, `preset_apply`, `template_render` | 中 |

---

## 3. 架构总览

### 3.1 工具层六层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 6: 应用层 (Application)                                        │
│  • AgentToolKit          - Agent专属工具包组装                       │
│  • ToolInspector         - 工具查看/调试界面                         │
│  • ToolPlayground        - 工具调用沙盒（开发调试用）                 │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 5: Agent集成层 (Agent Integration)                             │
│  • ToolEnabledAgent      - 支持工具调用的Agent基类                   │
│  • ToolCallParser        - LLM输出→工具调用解析                      │
│  • ToolResultFormatter   - 工具结果→LLM上下文格式化                   │
│  • ToolChainExecutor     - 多工具链式执行                            │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 4: 协议适配层 (Protocol Adapters)                              │
│  • MCPToolAdapter        - Model Context Protocol适配                │
│  • OpenAIFunctionAdapter - OpenAI Function Calling格式               │
│  • ClaudeToolAdapter     - Claude Tool Use格式                       │
│  • QwenToolAdapter       - 通义千问工具调用格式                       │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: 工具注册中心 (Tool Registry)                                │
│  • ToolRegistry          - 全局工具注册与发现                        │
│  • ToolSchemaGenerator   - 自动JSON Schema生成                       │
│  • ToolPermissionManager - 工具权限与作用域控制                       │
│  • ToolVersionManager    - 工具版本管理                              │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: 工具运行时 (Tool Runtime)                                   │
│  • ToolExecutor          - 异步工具执行引擎                          │
│  • ToolSandbox           - 工具执行隔离沙盒                          │
│  • ToolCircuitBreaker    - 熔断与降级                                │
│  • ToolMetricsCollector  - 调用指标采集                              │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 1: 领域工具集 (Domain Tools)                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ WorldSim    │ │ Memory      │ │ RAG         │ │ Config      │   │
│  │ Tools       │ │ Tools       │ │ Tools       │ │ Tools       │   │
│  │ (Step1)     │ │ (Step2)     │ │ (Step6)     │ │ (Step7)     │   │
│  ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤   │
│  │ LLM         │ │ Agent       │ │ Workflow    │ │ System      │   │
│  │ Tools       │ │ Tools       │ │ Tools       │ │ Tools       │   │
│  │ (Step3)     │ │ (Step4)     │ │ (Step5)     │ │ (通用)       │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 工具调用数据流

```
┌──────────┐     ┌─────────────────────────────────────────────────────┐
│  用户输入  │────→│ Agent.process()                                      │
│          │     │  - 构建System Prompt（注入可用工具Schema）            │
└──────────┘     │  - 调用LLM生成                                        │
                 │                                                      │
                 │  LLM输出:                                            │
                 │  {                                                   │
                 │    "thought": "需要查询角色背景",                       │
                 │    "tool_calls": [{                                  │
                 │      "name": "retrieve_character",                   │
                 │      "arguments": {"character_id": 42}              │
                 │    }]                                                │
                 │  }                                                   │
                 │         │                                            │
                 │         ▼                                            │
                 │  ┌─────────────┐                                    │
                 │  │ToolCallParser│ 解析LLM输出为结构化工具调用        │
                 │  └──────┬──────┘                                    │
                 │         │                                            │
                 │         ▼                                            │
                 │  ┌─────────────┐                                    │
                 │  │ToolPermission │ 检查Agent是否有权限调用此工具      │
                 │  │  Manager     │                                    │
                 │  └──────┬──────┘                                    │
                 │         │ 无权限 → 返回错误                           │
                 │         ▼ 有权限                                     │
                 │  ┌─────────────┐                                    │
                 │  │ToolExecutor  │ 异步执行工具（带超时/熔断）         │
                 │  │  (Sandbox)   │                                    │
                 │  └──────┬──────┘                                    │
                 │         │                                            │
                 │         ▼                                            │
                 │  ┌─────────────┐                                    │
                 │  │MetricsCollector│ 记录调用指标（延迟/成功/失败）    │
                 │  └──────┬──────┘                                    │
                 │         │                                            │
                 │         ▼                                            │
                 │  ┌─────────────┐                                    │
                 │  │ResultFormatter│ 格式化结果为LLM可理解的文本       │
                 │  └──────┬──────┘                                    │
                 │         │                                            │
                 └─────────┼────────────────────────────────────────────┘
                           ▼
                    ┌─────────────┐
                    │  返回给用户  │
                    │  （或继续   │
                    │  工具调用链）│
                    └─────────────┘
```

---

## 4. 核心组件设计

### 4.1 工具定义层 - `@tool`装饰器

**职责**: 声明式工具定义，一键生成Schema、注册到Registry

**参考**: LangChain `@tool` + MCP Tool Definition

```python
# src/deepnovel/tools/decorator.py

from typing import Any, Dict, List, Optional, Callable, TypeVar, ParamSpec
from dataclasses import dataclass, field
from enum import Enum
import inspect
import json
from functools import wraps

from pydantic import BaseModel, Field, create_model


class ToolCategory(str, Enum):
    """工具分类（对应各Step的领域）"""
    WORLD_SIM = "world_sim"          # Step1: 世界模拟
    MEMORY = "memory"                # Step2: 记忆系统
    LLM = "llm"                      # Step3: LLM层
    AGENT = "agent"                  # Step4: Agent协作
    WORKFLOW = "workflow"            # Step5: 任务调度
    RAG = "rag"                      # Step6: 检索增强
    CONFIG = "config"                # Step7: 配置系统
    SYSTEM = "system"                # 通用系统工具


class ToolScope(str, Enum):
    """工具作用域（权限级别）"""
    GLOBAL = "global"                # 任何Agent可调用
    RESTRICTED = "restricted"        # 需显式授权
    INTERNAL = "internal"            # 仅系统内部使用
    READONLY = "readonly"            # 只读工具（安全）


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    category: ToolCategory
    scope: ToolScope = ToolScope.GLOBAL
    version: str = "1.0"
    author: str = "system"
    deprecated: bool = False
    deprecated_reason: str = ""
    requires: List[str] = field(default_factory=list)  # 依赖的其他工具/服务
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """工具定义（运行时）"""
    metadata: ToolMetadata
    func: Callable
    schema: Dict[str, Any]          # JSON Schema for LLM function calling
    return_schema: Optional[Dict[str, Any]] = None
    is_async: bool = False
    is_generator: bool = False
    timeout: float = 30.0           # 默认超时30秒
    max_retries: int = 2
    circuit_breaker_threshold: int = 5


class ToolRegistry:
    """
    工具注册中心 - 全局单例

    职责：
    1. 工具注册与发现
    2. Schema管理
    3. 权限验证
    4. 版本控制
    """

    _instance: Optional['ToolRegistry'] = None
    _tools: Dict[str, ToolDefinition] = {}
    _categories: Dict[ToolCategory, List[str]] = {}
    _scopes: Dict[ToolScope, List[str]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, definition: ToolDefinition) -> 'ToolRegistry':
        """注册工具"""
        name = definition.metadata.name
        self._tools[name] = definition

        # 按分类索引
        cat = definition.metadata.category
        if cat not in self._categories:
            self._categories[cat] = []
        if name not in self._categories[cat]:
            self._categories[cat].append(name)

        # 按作用域索引
        scope = definition.metadata.scope
        if scope not in self._scopes:
            self._scopes[scope] = []
        if name not in self._scopes[scope]:
            self._scopes[scope].append(name)

        return self

    def get(self, name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self._tools.get(name)

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        scope: Optional[ToolScope] = None,
        include_deprecated: bool = False
    ) -> List[ToolDefinition]:
        """列出工具"""
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.metadata.category == category]
        if scope:
            tools = [t for t in tools if t.metadata.scope == scope]
        if not include_deprecated:
            tools = [t for t in tools if not t.metadata.deprecated]

        return tools

    def get_schemas_for_llm(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        获取LLM可用的工具Schema列表

        格式兼容 OpenAI Function Calling:
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": { ...JSON Schema... }
            }
        }
        """
        schemas = []
        tools = [self._tools[name] for name in tool_names] if tool_names else self._tools.values()

        for tool in tools:
            if tool.metadata.deprecated:
                continue
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.metadata.name,
                    "description": tool.metadata.description,
                    "parameters": tool.schema
                }
            })

        return schemas

    def has_permission(self, agent_tools: List[str], tool_name: str) -> bool:
        """检查Agent是否有权限调用工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            return False

        # 只读工具所有Agent可用
        if tool.metadata.scope == ToolScope.READONLY:
            return True

        # GLOBAL工具所有Agent可用
        if tool.metadata.scope == ToolScope.GLOBAL:
            return True

        # 其他需要显式授权
        return tool_name in agent_tools


def generate_schema_from_signature(func: Callable) -> Dict[str, Any]:
    """
    从函数签名自动生成JSON Schema

    使用Pydantic解析类型注解，生成符合JSON Schema Draft 7的规范
    """
    sig = inspect.signature(func)
    parameters = {}
    required = []

    for name, param in sig.parameters.items():
        if name == 'self' or name == 'cls':
            continue

        # 解析参数类型
        param_type = param.annotation
        if param_type is inspect.Parameter.empty:
            param_type = str

        # 构建Pydantic字段
        default = param.default if param.default is not inspect.Parameter.empty else ...
        if default is ...:
            required.append(name)

        # 简化：使用str表示
        parameters[name] = {"type": "string", "description": f"Parameter: {name}"}

    return {
        "type": "object",
        "properties": parameters,
        "required": required
    }


P = ParamSpec('P')
T = TypeVar('T')


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: ToolCategory = ToolCategory.SYSTEM,
    scope: ToolScope = ToolScope.GLOBAL,
    version: str = "1.0",
    timeout: float = 30.0,
    max_retries: int = 2,
    examples: Optional[List[Dict[str, Any]]] = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    工具装饰器

    用法：
        @tool(
            name="retrieve_character",
            description="检索角色信息",
            category=ToolCategory.RAG,
            scope=ToolScope.GLOBAL
        )
        def retrieve_character(character_id: int) -> Dict[str, Any]:
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or f"Tool: {tool_name}"

        # 生成JSON Schema
        schema = generate_schema_from_signature(func)

        # 构建元数据
        metadata = ToolMetadata(
            name=tool_name,
            description=tool_desc,
            category=category,
            scope=scope,
            version=version,
            examples=examples or []
        )

        # 构建定义
        definition = ToolDefinition(
            metadata=metadata,
            func=func,
            schema=schema,
            is_async=inspect.iscoroutinefunction(func),
            is_generator=inspect.isgeneratorfunction(func),
            timeout=timeout,
            max_retries=max_retries
        )

        # 注册到Registry
        registry = ToolRegistry()
        registry.register(definition)

        # 保留原函数
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return func(*args, **kwargs)

        # 附加工具元数据到函数
        wrapper._tool_definition = definition  # type: ignore
        wrapper._tool_name = tool_name  # type: ignore

        return wrapper

    return decorator
```

### 4.2 工具执行引擎

**职责**: 异步执行、超时控制、熔断降级、错误隔离

```python
# src/deepnovel/tools/executor.py

import asyncio
import time
import traceback
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from src.deepnovel.tools.decorator import ToolRegistry, ToolDefinition, ToolScope
from src.deepnovel.utils import get_logger

logger = get_logger()


class ToolExecutionStatus(str, Enum):
    """工具执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    CIRCUIT_OPEN = "circuit_open"
    FORBIDDEN = "forbidden"


@dataclass
class ToolExecutionResult:
    """工具执行结果"""
    tool_name: str
    status: ToolExecutionStatus
    output: Any = None
    error_message: str = ""
    execution_time_ms: float = 0.0
    retry_count: int = 0
    call_id: str = ""
    timestamp: float = field(default_factory=time.time)


class CircuitBreaker:
    """熔断器"""

    def __init__(self, threshold: int = 5, recovery_timeout: float = 30.0):
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> bool:
        """记录失败，返回是否触发熔断"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.threshold:
            self.state = "open"
            return True
        return False

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "half_open"
                return True
            return False
        return True  # half_open允许一次尝试


class ToolExecutor:
    """
    工具执行引擎

    特性：
    1. 异步执行（同步工具在线程池中运行）
    2. 超时控制
    3. 自动重试
    4. 熔断保护
    5. 并发限制（信号量）
    6. 执行指标记录
    """

    def __init__(self, max_concurrent: int = 50):
        self._registry = ToolRegistry()
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._thread_pool = ThreadPoolExecutor(max_workers=20)
        self._metrics: Dict[str, List[Dict[str, Any]]] = {}

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent_tools: Optional[List[str]] = None,
        call_id: Optional[str] = None
    ) -> ToolExecutionResult:
        """
        执行工具

        Args:
            tool_name: 工具名称
            arguments: 参数
            agent_tools: Agent授权的工具列表（None表示系统调用，不检查权限）
            call_id: 调用ID（用于追踪）

        Returns:
            ToolExecutionResult
        """
        start_time = time.time()
        call_id = call_id or f"{tool_name}_{int(start_time * 1000)}"

        # 1. 查找工具
        tool_def = self._registry.get(tool_name)
        if not tool_def:
            return ToolExecutionResult(
                tool_name=tool_name,
                status=ToolExecutionStatus.ERROR,
                error_message=f"Tool '{tool_name}' not found",
                call_id=call_id,
                execution_time_ms=0
            )

        # 2. 权限检查
        if agent_tools is not None and not self._registry.has_permission(agent_tools, tool_name):
            return ToolExecutionResult(
                tool_name=tool_name,
                status=ToolExecutionStatus.FORBIDDEN,
                error_message=f"Agent has no permission to call '{tool_name}'",
                call_id=call_id,
                execution_time_ms=0
            )

        # 3. 熔断检查
        cb = self._get_circuit_breaker(tool_name, tool_def.circuit_breaker_threshold)
        if not cb.can_execute():
            return ToolExecutionResult(
                tool_name=tool_name,
                status=ToolExecutionStatus.CIRCUIT_OPEN,
                error_message=f"Circuit breaker is open for '{tool_name}'",
                call_id=call_id,
                execution_time_ms=0
            )

        # 4. 执行（带超时和重试）
        async with self._semaphore:
            for attempt in range(tool_def.max_retries + 1):
                try:
                    if tool_def.is_async:
                        result = await asyncio.wait_for(
                            tool_def.func(**arguments),
                            timeout=tool_def.timeout
                        )
                    else:
                        loop = asyncio.get_event_loop()
                        result = await asyncio.wait_for(
                            loop.run_in_executor(self._thread_pool, lambda: tool_def.func(**arguments)),
                            timeout=tool_def.timeout
                        )

                    # 成功
                    cb.record_success()
                    elapsed = (time.time() - start_time) * 1000

                    self._record_metric(tool_name, "success", elapsed)

                    return ToolExecutionResult(
                        tool_name=tool_name,
                        status=ToolExecutionStatus.SUCCESS,
                        output=result,
                        execution_time_ms=elapsed,
                        retry_count=attempt,
                        call_id=call_id
                    )

                except asyncio.TimeoutError:
                    cb.record_failure()
                    self._record_metric(tool_name, "timeout", (time.time() - start_time) * 1000)

                    if attempt < tool_def.max_retries:
                        await asyncio.sleep(0.5 * (attempt + 1))  # 指数退避
                        continue

                    return ToolExecutionResult(
                        tool_name=tool_name,
                        status=ToolExecutionStatus.TIMEOUT,
                        error_message=f"Tool '{tool_name}' timed out after {tool_def.timeout}s",
                        execution_time_ms=(time.time() - start_time) * 1000,
                        retry_count=attempt,
                        call_id=call_id
                    )

                except Exception as e:
                    cb.record_failure()
                    self._record_metric(tool_name, "error", (time.time() - start_time) * 1000)

                    if attempt < tool_def.max_retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue

                    return ToolExecutionResult(
                        tool_name=tool_name,
                        status=ToolExecutionStatus.ERROR,
                        error_message=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
                        execution_time_ms=(time.time() - start_time) * 1000,
                        retry_count=attempt,
                        call_id=call_id
                    )

        # 不应该到达这里
        return ToolExecutionResult(
            tool_name=tool_name,
            status=ToolExecutionStatus.ERROR,
            error_message="Unexpected execution path",
            call_id=call_id
        )

    def _get_circuit_breaker(self, tool_name: str, threshold: int) -> CircuitBreaker:
        if tool_name not in self._circuit_breakers:
            self._circuit_breakers[tool_name] = CircuitBreaker(threshold=threshold)
        return self._circuit_breakers[tool_name]

    def _record_metric(self, tool_name: str, status: str, duration_ms: float):
        if tool_name not in self._metrics:
            self._metrics[tool_name] = []
        self._metrics[tool_name].append({
            "status": status,
            "duration_ms": duration_ms,
            "timestamp": time.time()
        })

    def get_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取工具执行指标"""
        if tool_name:
            metrics = self._metrics.get(tool_name, [])
            if not metrics:
                return {}
            return {
                "total_calls": len(metrics),
                "success_rate": sum(1 for m in metrics if m["status"] == "success") / len(metrics),
                "avg_duration_ms": sum(m["duration_ms"] for m in metrics) / len(metrics),
                "error_rate": sum(1 for m in metrics if m["status"] == "error") / len(metrics)
            }

        return {name: self.get_metrics(name) for name in self._metrics}
```

### 4.3 支持工具的Agent基类

**职责**: 让Agent能够使用LLM函数调用、解析工具调用、执行工具链

```python
# src/deepnovel/tools/agent_integration.py

import json
import re
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from src.deepnovel.agents.base import BaseAgent, AgentConfig, Message, MessageType
from src.deepnovel.tools.decorator import ToolRegistry
from src.deepnovel.tools.executor import ToolExecutor, ToolExecutionResult, ToolExecutionStatus
from src.deepnovel.utils import get_logger

logger = get_logger()


class ToolCall:
    """LLM输出的工具调用"""
    def __init__(self, name: str, arguments: Dict[str, Any], id: Optional[str] = None):
        self.name = name
        self.arguments = arguments
        self.id = id or f"call_{name}"


class ToolEnabledAgent(BaseAgent, ABC):
    """
    支持工具调用的Agent基类

    继承此类即可让Agent具备：
    1. LLM函数调用能力（自动注入可用工具Schema）
    2. 工具调用解析与执行
    3. 工具结果回注到对话上下文
    4. 多轮工具调用链支持
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._tool_executor = ToolExecutor()
        self._tool_registry = ToolRegistry()
        self._max_tool_iterations = 5  # 防止无限工具调用
        self._available_tools: List[str] = config.tools or []

        # 如果没有指定工具，默认加载同分类的所有工具
        if not self._available_tools:
            self._available_tools = self._auto_discover_tools()

    def _auto_discover_tools(self) -> List[str]:
        """自动发现适合本Agent的工具"""
        # 子类可重写此方法
        return []

    def _build_system_prompt_with_tools(self, base_prompt: str) -> str:
        """
        在System Prompt中注入工具说明

        优先使用Step9的PromptComposer进行声明式模板组装。
        当PromptComposer不可用时，回退到字符串拼接方式。
        """
        schemas = self._tool_registry.get_schemas_for_llm(self._available_tools)

        if not schemas:
            return base_prompt

        # 首选：使用Step9的PromptComposer（冲突D解决方案）
        try:
            from src.deepnovel.prompts.composer import PromptComposer
            composer = PromptComposer()
            return composer.compose(
                "tool_enabled_agent",
                params={
                    "base_role": base_prompt,
                    "available_tools": schemas,
                    "reasoning_mode": getattr(self, '_reasoning_mode', 'cot')
                }
            )
        except ImportError:
            # 回退：字符串拼接（向后兼容）
            pass

        tools_text = "\n\n## 可用工具\n\n你可以使用以下工具辅助完成任务：\n\n"
        for schema in schemas:
            func = schema["function"]
            tools_text += f"### {func['name']}\n"
            tools_text += f"描述: {func['description']}\n"
            tools_text += f"参数: {json.dumps(func['parameters'], ensure_ascii=False, indent=2)}\n\n"

        tools_text += """
使用工具时，请按以下JSON格式输出：
```tool_call
{
  "tool_calls": [
    {
      "name": "工具名称",
      "arguments": {"参数名": "参数值"}
    }
  ]
}
```
"""
        return base_prompt + tools_text

    def _parse_tool_calls(self, llm_output: str) -> List[ToolCall]:
        """
        从LLM输出中解析工具调用

        支持格式：
        1. ```tool_call {...} ```
        2. JSON中嵌套的 tool_calls 字段
        """
        tool_calls = []

        # 尝试匹配 ```tool_call 代码块
        pattern = r'```tool_call\s*\n?(.*?)\n?```'
        matches = re.findall(pattern, llm_output, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match.strip())
                calls = data.get("tool_calls", [])
                for call in calls:
                    tool_calls.append(ToolCall(
                        name=call["name"],
                        arguments=call.get("arguments", {}),
                        id=call.get("id")
                    ))
            except (json.JSONDecodeError, KeyError):
                continue

        return tool_calls

    def _format_tool_result(self, result: ToolExecutionResult) -> str:
        """格式化工具结果为LLM可理解的文本"""
        if result.status == ToolExecutionStatus.SUCCESS:
            output = result.output
            if isinstance(output, dict):
                return json.dumps(output, ensure_ascii=False, indent=2)
            return str(output)
        else:
            return f"[工具调用失败] {result.status}: {result.error_message}"

    async def generate_with_tools(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        带工具调用的生成

        流程：
        1. 构建含工具说明的System Prompt
        2. 调用LLM生成
        3. 解析工具调用
        4. 执行工具
        5. 将结果回注，再次调用LLM
        6. 重复3-5直到无工具调用或达到最大迭代次数
        """
        # 构建带工具的System Prompt
        effective_system = self._build_system_prompt_with_tools(system_prompt or "")

        # 构建对话历史
        messages = []
        if effective_system:
            messages.append({"role": "system", "content": effective_system})
        messages.append({"role": "user", "content": prompt})

        for iteration in range(self._max_tool_iterations):
            # 调用LLM
            llm_response = self._generate_with_llm(
                prompt=prompt if iteration == 0 else self._build_tool_result_prompt(messages),
                system_prompt=effective_system if iteration == 0 else None,
                timeout=kwargs.get("timeout", self.config.timeout)
            )

            if not llm_response:
                return "[LLM调用失败]"

            # 解析工具调用
            tool_calls = self._parse_tool_calls(llm_response)

            if not tool_calls:
                # 无工具调用，直接返回
                return llm_response

            # 执行工具
            tool_results = []
            for tc in tool_calls:
                result = await self._tool_executor.execute(
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    agent_tools=self._available_tools
                )
                tool_results.append(result)

            # 构建下一轮Prompt
            messages.append({"role": "assistant", "content": llm_response})

            results_text = "\n\n".join([
                f"工具 '{r.tool_name}' 结果:\n{self._format_tool_result(r)}"
                for r in tool_results
            ])
            messages.append({"role": "user", "content": f"工具执行结果:\n\n{results_text}\n\n请基于以上结果继续回答。"})

        # 达到最大迭代次数
        return "[达到最大工具调用次数限制]"

    def _build_tool_result_prompt(self, messages: List[Dict[str, str]]) -> str:
        """构建包含工具结果的Prompt"""
        # 简化实现：返回最后一条用户消息
        for msg in reversed(messages):
            if msg["role"] == "user":
                return msg["content"]
        return ""
```

### 4.4 Embedding工具链（Step3/Step6核心依赖）

**职责**: 为RAG和记忆系统提供真正的语义向量化能力

```python
# src/deepnovel/tools/embeddings.py

from typing import List, Dict, Any, Optional
import asyncio
import hashlib
from abc import ABC, abstractmethod

from src.deepnovel.tools.decorator import tool, ToolCategory, ToolScope


class BaseEmbeddingEngine(ABC):
    """嵌入引擎基类"""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class SentenceTransformerEngine(BaseEmbeddingEngine):
    """本地SentenceTransformers引擎"""

    def __init__(self, model_name: str = "BAAI/bge-large-zh-v1.5"):
        self.model_name = model_name
        self._model = None
        self._dimension = 1024

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    def embed(self, text: str) -> List[float]:
        model = self._load_model()
        return model.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension


class APIEmbeddingEngine(BaseEmbeddingEngine):
    """云端API嵌入引擎（OpenAI/Qwen等）"""

    def __init__(self, provider: str, model: str, api_key: str):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self._dimension = 1536  # OpenAI默认

    def embed(self, text: str) -> List[float]:
        # 具体实现依赖各适配器
        raise NotImplementedError(f"API embedding for {self.provider} not implemented")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


class EmbeddingRouter:
    """
    嵌入路由

    根据质量/速度/成本需求选择不同引擎
    """

    def __init__(self):
        self._engines: Dict[str, BaseEmbeddingEngine] = {}
        self._default_engine: Optional[str] = None

    def register_engine(self, name: str, engine: BaseEmbeddingEngine, is_default: bool = False):
        self._engines[name] = engine
        if is_default or self._default_engine is None:
            self._default_engine = name

    def get_engine(self, name: Optional[str] = None) -> BaseEmbeddingEngine:
        engine_name = name or self._default_engine
        if engine_name not in self._engines:
            raise ValueError(f"Embedding engine '{engine_name}' not found")
        return self._engines[engine_name]


# 全局路由实例
_embedding_router = EmbeddingRouter()


def get_embedding_router() -> EmbeddingRouter:
    return _embedding_router


# ===== 工具定义 =====

@tool(
    name="embed_text",
    description="将文本转换为向量嵌入，用于语义检索和相似度计算",
    category=ToolCategory.LLM,
    scope=ToolScope.GLOBAL,
    timeout=10.0
)
def embed_text(text: str, engine: str = "default") -> Dict[str, Any]:
    """
    嵌入文本工具

    Args:
        text: 要嵌入的文本
        engine: 引擎名称（default/local/api）

    Returns:
        {"embedding": [...], "dimension": 1024, "engine": "..."}
    """
    router = get_embedding_router()
    eng = router.get_engine(engine if engine != "default" else None)
    embedding = eng.embed(text)
    return {
        "embedding": embedding,
        "dimension": eng.dimension,
        "engine": engine
    }


@tool(
    name="embed_batch",
    description="批量嵌入多条文本",
    category=ToolCategory.LLM,
    scope=ToolScope.GLOBAL,
    timeout=30.0
)
def embed_batch(texts: List[str], engine: str = "default") -> Dict[str, Any]:
    """批量嵌入"""
    router = get_embedding_router()
    eng = router.get_engine(engine if engine != "default" else None)
    embeddings = eng.embed_batch(texts)
    return {
        "embeddings": embeddings,
        "count": len(texts),
        "dimension": eng.dimension
    }


@tool(
    name="calculate_similarity",
    description="计算两段文本的语义相似度（余弦相似度）",
    category=ToolCategory.LLM,
    scope=ToolScope.GLOBAL
)
def calculate_similarity(text1: str, text2: str) -> Dict[str, Any]:
    """计算文本相似度"""
    router = get_embedding_router()
    eng = router.get_engine(None)

    emb1 = eng.embed(text1)
    emb2 = eng.embed(text2)

    # 余弦相似度
    dot = sum(a * b for a, b in zip(emb1, emb2))
    norm1 = sum(a * a for a in emb1) ** 0.5
    norm2 = sum(b * b for b in emb2) ** 0.5
    similarity = dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

    return {
        "similarity": round(similarity, 4),
        "text1_preview": text1[:50],
        "text2_preview": text2[:50]
    }
```

### 4.5 领域工具集示例

#### 4.5.1 RAG检索工具（Step6）

```python
# src/deepnovel/tools/domain/rag_tools.py

from typing import Dict, Any, List, Optional
from src.deepnovel.tools.decorator import tool, ToolCategory, ToolScope


@tool(
    name="retrieve_world_knowledge",
    description="检索世界观知识：世界规则、地理、历史、魔法体系等",
    category=ToolCategory.RAG,
    scope=ToolScope.GLOBAL,
    timeout=5.0
)
def retrieve_world_knowledge(
    query: str,
    top_k: int = 5,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    检索世界知识

    Args:
        query: 查询内容（如"修仙境界划分"）
        top_k: 返回结果数量
        filters: 过滤条件 {"category": "cultivation", "world_id": "..."}
    """
    # 实际实现依赖Step6的RAG架构
    # 此处为接口定义
    return {
        "results": [],
        "query": query,
        "total_found": 0
    }


@tool(
    name="retrieve_character_memory",
    description="检索角色记忆：性格、经历、关系、当前状态",
    category=ToolCategory.RAG,
    scope=ToolScope.GLOBAL,
    timeout=5.0
)
def retrieve_character_memory(
    character_id: int,
    query: str,
    memory_type: str = "all",  # all/episodic/semantic/emotional
    top_k: int = 5
) -> Dict[str, Any]:
    """检索角色记忆"""
    return {
        "character_id": character_id,
        "memories": [],
        "query": query
    }


@tool(
    name="retrieve_plot_continuity",
    description="检索情节连贯性信息：前文摘要、伏笔、未解决冲突",
    category=ToolCategory.RAG,
    scope=ToolScope.GLOBAL,
    timeout=5.0
)
def retrieve_plot_continuity(
    current_chapter: int,
    query: str = "",
    lookback_chapters: int = 3
) -> Dict[str, Any]:
    """检索情节连贯性"""
    return {
        "chapter": current_chapter,
        "summaries": [],
        "foreshadowing": [],
        "unresolved_conflicts": []
    }


@tool(
    name="retrieve_style_reference",
    description="检索风格参考：修辞手法、叙事模式、作者风格范例",
    category=ToolCategory.RAG,
    scope=ToolScope.GLOBAL,
    timeout=5.0
)
def retrieve_style_reference(
    style_type: str,  # narrative/dialogue/description/pacing
    query: str,
    top_k: int = 3
) -> Dict[str, Any]:
    """检索风格参考"""
    return {
        "style_type": style_type,
        "examples": [],
        "techniques": []
    }
```

#### 4.5.2 世界模拟工具（Step1）

```python
# src/deepnovel/tools/domain/world_tools.py

from typing import Dict, Any, List, Optional
from src.deepnovel.tools.decorator import tool, ToolCategory, ToolScope


@tool(
    name="fact_query",
    description="查询世界事实：角色属性、实体关系、世界规则",
    category=ToolCategory.WORLD_SIM,
    scope=ToolScope.GLOBAL,
    timeout=3.0
)
def fact_query(
    subject: Optional[str] = None,
    predicate: Optional[str] = None,
    time_point: Optional[int] = None,
    fact_type: str = "all"  # all/attribute/relation/possession/event/rule
) -> Dict[str, Any]:
    """查询世界事实"""
    return {"facts": [], "count": 0}


@tool(
    name="fact_set",
    description="设置世界事实（自动处理时间范围和因果传播）",
    category=ToolCategory.WORLD_SIM,
    scope=ToolScope.RESTRICTED,  # 需要授权，影响世界状态
    timeout=5.0
)
def fact_set(
    subject: str,
    predicate: str,
    value: Any,
    fact_type: str = "attribute",
    confidence: float = 1.0,
    auto_propagate: bool = True
) -> Dict[str, Any]:
    """设置世界事实"""
    return {"fact_id": None, "propagated": 0}


@tool(
    name="causal_trace",
    description="追溯因果关系：查找某事实的原因链或结果链",
    category=ToolCategory.WORLD_SIM,
    scope=ToolScope.GLOBAL,
    timeout=10.0
)
def causal_trace(
    fact_id: int,
    direction: str = "backward",  # backward/forward/both
    max_depth: int = 5
) -> Dict[str, Any]:
    """追溯因果链"""
    return {"chain": [], "depth": 0}
```

#### 4.5.3 记忆管理工具（Step2）

```python
# src/deepnovel/tools/domain/memory_tools.py

from typing import Dict, Any, List
from src.deepnovel.tools.decorator import tool, ToolCategory, ToolScope


@tool(
    name="memory_store",
    description="存储记忆到长期记忆库",
    category=ToolCategory.MEMORY,
    scope=ToolScope.RESTRICTED,
    timeout=3.0
)
def memory_store(
    content: str,
    character_id: Optional[int] = None,
    memory_type: str = "episodic",  # episodic/semantic/emotional/procedural
    importance: float = 0.5,
    tags: List[str] = None
) -> Dict[str, Any]:
    """存储记忆"""
    return {"memory_id": None, "status": "stored"}


@tool(
    name="memory_retrieve",
    description="从记忆库检索相关记忆（支持语义搜索）",
    category=ToolCategory.MEMORY,
    scope=ToolScope.GLOBAL,
    timeout=5.0
)
def memory_retrieve(
    query: str,
    character_id: Optional[int] = None,
    memory_type: str = "all",
    top_k: int = 5,
    min_importance: float = 0.0
) -> Dict[str, Any]:
    """检索记忆"""
    return {"memories": [], "total": 0}
```

#### 4.5.4 配置管理工具（Step7）

```python
# src/deepnovel/tools/domain/config_tools.py

from typing import Dict, Any, List
from src.deepnovel.tools.decorator import tool, ToolCategory, ToolScope


@tool(
    name="config_validate",
    description="验证小说配置是否符合Schema规范",
    category=ToolCategory.CONFIG,
    scope=ToolScope.GLOBAL,
    timeout=2.0
)
def config_validate(config_json: str) -> Dict[str, Any]:
    """验证配置"""
    return {"valid": True, "errors": []}


@tool(
    name="preset_apply",
    description="应用配置预设（如修仙/武侠/科幻等）",
    category=ToolCategory.CONFIG,
    scope=ToolScope.GLOBAL,
    timeout=2.0
)
def preset_apply(
    preset_name: str,
    base_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """应用预设"""
    return {"preset": preset_name, "config": {}}
```

### 4.6 MCP兼容层

**职责**: 让本系统的工具可以被外部MCP客户端调用，也可以调用外部MCP服务

```python
# src/deepnovel/tools/mcp_adapter.py

from typing import Any, Dict, List, Optional
import json

from src.deepnovel.tools.decorator import ToolRegistry, ToolDefinition


class MCPToolAdapter:
    """
    Model Context Protocol 工具适配器

    参考: https://modelcontextprotocol.io/

    提供：
    1. 将内部工具导出为MCP格式
    2. 将MCP外部工具导入为内部工具
    3. MCP服务端/客户端实现
    """

    @staticmethod
    def to_mcp_format(tool_def: ToolDefinition) -> Dict[str, Any]:
        """将内部工具转换为MCP工具格式"""
        return {
            "name": tool_def.metadata.name,
            "description": tool_def.metadata.description,
            "inputSchema": tool_def.schema,
            "annotations": {
                "title": tool_def.metadata.name,
                "readOnlyHint": tool_def.metadata.scope.value == "readonly",
                "deprecated": tool_def.metadata.deprecated
            }
        }

    @staticmethod
    def from_mcp_format(mcp_tool: Dict[str, Any]) -> Dict[str, Any]:
        """从MCP格式解析工具定义"""
        return {
            "name": mcp_tool["name"],
            "description": mcp_tool.get("description", ""),
            "schema": mcp_tool.get("inputSchema", {})
        }

    def export_all_tools(self) -> List[Dict[str, Any]]:
        """导出所有工具为MCP格式"""
        registry = ToolRegistry()
        return [self.to_mcp_format(t) for t in registry.list_tools()]

    def create_mcp_server_handler(self) -> Callable:
        """创建MCP服务端处理器（供外部调用）"""
        # 实际实现需要集成MCP SDK
        # 此处为接口定义
        async def handle_request(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
            if method == "tools/list":
                return {"tools": self.export_all_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                # 调用内部工具执行
                return {"result": "not implemented"}
            return {"error": "Unknown method"}

        return handle_request
```

---

## 5. 工具层与其他层的集成关系

### 5.1 与Step1（数据层）的集成

```
世界模拟工具 ←→ FactManager/EntityManager
  - fact_set/fact_query 直接操作Step1的数据层
  - causal_trace 调用Step1的因果推理引擎
  - mind_simulate 调用Step1的角色心智模拟
```

### 5.2 与Step2（记忆系统）的集成

```
记忆工具 ←→ MemoryManager (三级阶梯)
  - memory_store → 长期记忆库 (SQLite + Qdrant)
  - memory_retrieve → 向量语义检索 + 时序查询
  - 嵌入工具为记忆提供向量化能力
```

### 5.3 与Step3（LLM层）的集成

```
LLM工具 ←→ LLMRouter/适配器
  - llm_generate 调用各提供商API
  - embed_text/embed_batch 提供向量化
  - model_info 查询模型能力与状态
```

### 5.4 与Step4（Agent层）的集成

```
Agent工具 ←→ EventBus/StateManager
  - agent_message → EventBus.publish
  - agent_handoff → 状态转移
  - state_read/state_write → 共享状态区
```

### 5.5 与Step5（任务调度）的集成

```
工作流工具 ←→ WorkflowEngine/TaskScheduler
  - workflow_create → 创建状态图
  - task_submit → 提交到调度队列
  - checkpoint_save → CheckpointManager
```

### 5.6 与Step6（RAG）的集成

```
检索工具 ←→ RAG Pipeline
  - retrieve_* → 领域检索器
  - embed_text → Embedding引擎
  - calculate_similarity → 向量运算
```

### 5.7 与Step7（配置系统）的集成

```
配置工具 ←→ ConfigComposer/PresetManager
  - config_validate → Pydantic验证
  - preset_apply → 预设库查询
  - template_render → Jinja2引擎
```

---

## 6. 实施计划

### Phase 1: 基础设施（第1-3天）

| 任务 | 文件 | 内容 |
|------|------|------|
| 创建工具装饰器 | `tools/decorator.py` | `@tool`装饰器、ToolRegistry、Schema生成 |
| 创建执行引擎 | `tools/executor.py` | ToolExecutor、熔断器、并发控制 |
| 创建Agent集成 | `tools/agent_integration.py` | ToolEnabledAgent、ToolCallParser |

**验收标准**:
- `@tool`装饰器可以注册函数并生成JSON Schema
- ToolRegistry可以列出、查询、权限检查
- ToolExecutor可以异步执行带超时和重试

### Phase 2: Embedding实现（第4-6天）

| 任务 | 文件 | 内容 |
|------|------|------|
| Embedding引擎 | `tools/embeddings.py` | SentenceTransformerEngine、APIEmbeddingEngine、EmbeddingRouter |
| LLM适配器实现 | `llm/adapters/*/embedding.py` | 各提供商embed方法实现 |
| 嵌入工具 | `tools/domain/embedding_tools.py` | embed_text/embed_batch/calculate_similarity |

**验收标准**:
- `embed_text`工具可正常调用并返回向量
- 支持本地模型（BAAI/bge-large-zh）和API模型
- 与现有ChromaDB/Qdrant集成测试通过

### Phase 3: 领域工具集（第7-10天）

| 任务 | 文件 | 内容 |
|------|------|------|
| RAG检索工具 | `tools/domain/rag_tools.py` | retrieve_world/character/plot/style |
| 世界模拟工具 | `tools/domain/world_tools.py` | fact_query/set、causal_trace |
| 记忆管理工具 | `tools/domain/memory_tools.py` | memory_store/retrieve |
| 配置管理工具 | `tools/domain/config_tools.py` | config_validate、preset_apply |
| LLM工具 | `tools/domain/llm_tools.py` | llm_generate、model_info |
| Agent协作工具 | `tools/domain/agent_tools.py` | agent_message、handoff |
| 工作流工具 | `tools/domain/workflow_tools.py` | task_submit、workflow_create |

**验收标准**:
- 每个领域至少3个可用工具
- 工具Schema正确生成，LLM可以理解
- 工具权限系统正常工作

### Phase 4: Agent改造（第11-12天）

| 任务 | 文件 | 内容 |
|------|------|------|
| 改造BaseAgent | `agents/base.py` | 移除硬编码_execute_tool，继承ToolEnabledAgent |
| 改造各Agent | `agents/*.py` | 为每个Agent配置合适的工具集 |
| 工具调用链路 | `tools/chain.py` | 支持工具链式调用和条件分支 |

**验收标准**:
- Agent可以接收LLM的工具调用指令并执行
- 工具执行结果正确回注到对话上下文
- 多轮工具调用链正常工作

### Phase 5: MCP兼容与监控（第13-14天）

| 任务 | 文件 | 内容 |
|------|------|------|
| MCP适配器 | `tools/mcp_adapter.py` | MCP格式转换、服务端处理器 |
| 工具监控 | `tools/metrics.py` | 调用指标聚合、慢查询检测 |
| 工具调试界面 | API端点 | /tools/list、/tools/execute、/tools/metrics |

**验收标准**:
- 工具列表可导出为MCP格式
- 工具调用指标可查询（成功率/延迟/错误率）
- 提供HTTP API供前端调试工具

---

## 7. 迁移策略

### 7.1 存量代码处理

| 组件 | 处理方式 | 说明 |
|------|---------|------|
| `BaseAgent._execute_tool()` | **删除** | 被ToolExecutor取代 |
| `AgentConfig.tools: List[str]` | **保留兼容** | 字符串列表映射到ToolRegistry查询 |
| `EmbeddingClient` | **改造实现** | 各适配器实现embed/embed_batch |
| `agents/hook_generator.py` | **改造** | 内存cosine similarity → 调用retrieve_*工具 |
| `agents/config_enhancer.py` | **改造** | 规则扩展 → 调用LLM工具 + config_validate |

### 7.2 渐进式迁移路径

```
第1周: 工具基础设施 + Embedding实现
  └─ 新系统并行运行，旧系统不动

第2周: 领域工具开发 + 单个Agent试点
  └─ 选择world_builder作为试点，赋予fact_*和retrieve_*工具

第3周: 全面Agent改造
  └─ 所有Agent迁移到ToolEnabledAgent基类

第4周: 旧代码清理
  └─ 删除BaseAgent._execute_tool、HashEmbeddingFunction等死代码
```

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Embedding模型加载慢 | 首次调用延迟高 | 懒加载 + 预加载机制；提供轻量fallback模型 |
| 工具Schema与LLM不匹配 | 工具调用解析失败 | 多格式支持（JSON/XML/Markdown）；严格验证 |
| 工具权限过于严格 | Agent无法完成工作 | 默认开放READONLY工具；逐步收紧权限 |
| 工具调用循环 | 无限递归 | max_tool_iterations限制；调用深度检测 |
| 工具执行阻塞 | 拖垮整个系统 | 熔断器 + 超时 + 线程池隔离 |

---

## 9. 成功指标

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|---------|
| 可用工具数量 | 8（硬编码） | 30+ | `ToolRegistry.list_tools()`计数 |
| Embedding实现覆盖率 | 0% | 100% | 所有适配器实现embed方法 |
| Agent工具调用成功率 | N/A | >95% | ToolMetrics统计 |
| 工具平均执行延迟 | N/A | <500ms | ToolMetrics统计 |
| LLM工具调用解析成功率 | N/A | >90% | 解析成功/总调用次数 |
| MCP兼容性 | 0% | 100% | Schema可通过MCP验证 |
