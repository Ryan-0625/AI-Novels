# Step 5: 任务调度层重构 - 可视化驱动的工作流编排

> 版本: 1.0
> 日期: 2026-04-28
> 依赖: Step1 (数据层), Step2 (记忆系统), Step3 (LLM层), Step4 (Agent层)
> 目标: 构建可视化驱动、事件驱动、持久化的任务调度与编排系统

---

## 1. 设计哲学

### 1.1 核心转变

```
从：单体Coordinator (1280行硬编码DAG)  → 到：分层调度架构（引擎+调度器+可视化）
从：内存任务状态 (丢失即无)             → 到：持久化任务队列 (数据库+事件日志)
从：轮询状态查询 (3秒刷新)               → 到：实时事件推送 (WebSocket + SSE)
从：无DAG可视化                         → 到：交互式工作流图 (D3.js + 状态着色)
从：静态进度条                         → 到：动态执行时间线 (Gantt + 火焰图)
从：RocketMQ mock模式                  → 到：EventBus原生集成 (去中间件化)
```

### 1.2 设计原则

1. **可见即可信**: 每个任务状态变化必须实时反映到可视化界面，延迟 < 500ms
2. **编排即代码**: DAG定义使用Python原生代码（非YAML/JSON），支持条件分支和动态节点
3. **事件即真相**: 所有状态变更必须通过EventBus发布事件，可视化层只订阅事件
4. **断点即常态**: 任意节点失败后支持从断点恢复，无需重新执行已成功节点
5. **调度即策略**: 支持优先级队列、资源限制、并发控制、延迟调度等高级策略

### 1.3 行业前沿参考

| 来源 | 核心借鉴 | 适用场景 |
|------|---------|---------|
| **Prefect 3.0** (2024) | 事件驱动工作流、原生async、装饰器定义DAG | 轻量级Python工作流 |
| **Dagster** (2024) | 软件定义资产、数据血缘追踪、丰富可视化 | 数据/AI流水线 |
| **Temporal** (2024) | 可靠状态机、可视化历史重放、故障恢复 | 长时运行工作流 |
| **LangGraph** (2025) | 状态图执行、增量更新、Checkpoint | AI Agent编排 |
| **Ray** (2024) | 分布式Actor、资源调度、任务并行 | 大规模AI计算 |
| **Argo Workflows** (2024) | DAG可视化、K8s原生、Cron调度 | 云原生编排 |
| **Flyte** (2024) | 类型安全、版本化工作流、缓存 | ML流水线 |

---

## 2. 现状诊断

### 2.1 当前组件清单

| 组件 | 文件 | 问题 | 处置 |
|------|------|------|------|
| CoordinatorAgent | `agents/coordinator.py` (1280行) | 单体过重、无持久化、无checkpoint、DAG每请求重建 | **重构为TaskOrchestrator + TaskScheduler** |
| TaskManagerAgent | `agents/task_manager.py` (551行) | 内存状态机、字符串匹配路由、线程不安全 | **合并到TaskScheduler** |
| WorkflowOrchestrator | `agents/workflow_orchestrator.py` | 未实际使用、与coordinator功能重叠 | **删除** |
| EnhancedWorkflowOrchestrator | `agents/enhanced_workflow_orchestrator.py` | 过度工程化、未使用 | **删除** |
| RocketMQ Producer | `messaging/rocketmq_producer.py` | mock模式、无延迟发送 | **删除** |
| RocketMQ Consumer | `messaging/rocketmq_consumer.py` | mock模式、处理器为空 | **删除** |
| PerformanceMonitor | `core/performance_monitor.py` | 内存指标、无导出、无可视化 | **重构为MetricsCollector + 可视化导出** |
| EventBus | `core/event_bus.py` | 设计良好但未集成到任务执行 | **增强并作为核心基础设施** |

### 2.2 前端现状

| 组件 | 文件 | 问题 |
|------|------|------|
| TaskMonitorView | `frontend/src/views/TaskMonitorView.vue` | 轮询3秒刷新、无DAG可视化、无实时推送 |
| SystemHealthView | `frontend/src/views/SystemHealthView.vue` | 仅显示组件健康、无任务级监控 |
| SystemHealthPanel | `frontend/src/components/SystemHealthPanel.vue` | 同上 |
| API服务 | `frontend/src/services/api.ts` | 纯REST轮询、无WebSocket |

---

## 3. 架构总览

### 3.1 五层调度架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 5: 可视化层 (Visualization)                                    │
│  • WorkflowGraphView     - 交互式DAG图 (D3.js + Vue3)               │
│  • TaskTimelineView      - 执行时间线/Gantt图                        │
│  • RealtimeDashboard     - 实时指标面板 (WebSocket推送)              │
│  • ExecutionTraceView    - 执行轨迹回放                             │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 4: API网关层 (API Gateway)                                     │
│  • REST API              - 任务CRUD、状态查询                        │
│  • WebSocket Endpoint    - 实时事件推送                              │
│  • SSE Stream            - 任务日志流                                │
│  • GraphQL (可选)         - 复杂查询聚合                             │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: 编排引擎层 (Orchestration Engine)                           │
│  • TaskOrchestrator      - 状态图执行 (LangGraph模式)                │
│  • TaskScheduler         - 任务队列/优先级/并发控制                   │
│  • CheckpointManager     - 断点持久化与恢复                          │
│  • ResourceLimiter       - 资源限制与背压                            │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: 事件基础设施层 (Event Infrastructure)                        │
│  • EventBus              - 发布订阅 (已存在，增强集成)                │
│  • EventStore            - 事件持久化 (SQLite时序表)                 │
│  • EventReplayer         - 事件回放与调试                            │
│  • MetricsCollector      - 指标采集与聚合                            │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 1: 持久化层 (Persistence)                                      │
│  • SQLite                - 任务/工作流/事件存储                      │
│  • File System           - Checkpoint大对象、日志文件                │
│  • Qdrant (可选)          - 事件语义检索                             │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流设计

```
用户创建任务
    │
    ▼
┌──────────────┐    POST /tasks    ┌──────────────┐
│   前端界面   │ ────────────────→ │  FastAPI     │
│  (Vue3+D3)   │                   │  (REST+WS)   │
└──────────────┘                   └──────┬───────┘
    │                                     │
    │ WebSocket 实时推送                   │
    │◄────────────────────────────────────┤
    │                                     ▼
    │                            ┌──────────────┐
    │                            │ TaskScheduler│
    │                            │  (任务队列)   │
    │                            └──────┬───────┘
    │                                   │ dequeue
    │                                   ▼
    │                            ┌──────────────┐
    │                            │TaskOrchestrator│
    │                            │  (状态图执行) │
    │                            └──────┬───────┘
    │                                   │
    │              ┌────────────────────┼────────────────────┐
    │              │                    │                    │
    │              ▼                    ▼                    ▼
    │       ┌──────────┐       ┌──────────┐       ┌──────────┐
    │       │  Agent   │       │  Agent   │       │  Agent   │
    │       │  Node A  │       │  Node B  │       │  Node C  │
    │       └────┬─────┘       └────┬─────┘       └────┬─────┘
    │            │                  │                  │
    │            └──────────────────┼──────────────────┘
    │                               │
    │                               ▼
    │                        ┌──────────────┐
    │                        │   EventBus   │
    │                        │  (状态变更)   │
    │                        └──────┬───────┘
    │                               │
    │         ┌─────────────────────┼─────────────────────┐
    │         │                     │                     │
    │         ▼                     ▼                     ▼
    │  ┌──────────┐         ┌──────────┐         ┌──────────┐
    │  │ EventStore│         │Metrics   │         │ WebSocket│
    │  │(持久化)   │         │Collector │         │ Handler  │
    │  └──────────┘         └──────────┘         └────┬─────┘
    │                                                 │
    │◄────────────────────────────────────────────────┘
    │
    ▼
┌──────────────┐
│  可视化更新   │
│ DAG着色/进度  │
└──────────────┘
```

---

## 4. 核心组件设计

### 4.1 TaskOrchestrator - 任务编排引擎

> **命名变更说明**: 原名 `WorkflowEngine`，为避免与 Step4 Agent层的编排器混淆，更名为 `TaskOrchestrator`。
> 职责不变：状态图编译、节点执行、状态流转、并行控制。

**职责**: 状态图编译、节点执行、状态流转、并行控制

**参考**: LangGraph StateGraph + Prefect 3.0 Flow

**实现模板**:

```python
# src/deepnovel/scheduling/workflow_engine.py

from typing import Any, Dict, List, Optional, Callable, Coroutine, Set, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
import asyncio
import time
import uuid
from collections import defaultdict

from src.deepnovel.core.event_bus import EventBus, EventType, Event, EventPriority
from src.deepnovel.core.performance_monitor import MetricsCollector
from src.deepnovel.utils import get_logger

logger = get_logger()


class NodeStatus(Enum):
    """节点执行状态"""
    PENDING = "pending"
    SCHEDULED = "scheduled"      # 已入队等待执行
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"          # 条件分支未命中
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowStatus(Enum):
    """工作流状态"""
    CREATED = "created"
    COMPILING = "compiling"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class NodeDefinition:
    """节点定义"""
    node_id: str
    agent_name: str                          # 关联的Agent名称
    process_func: Callable                   # 处理函数
    dependencies: List[str] = field(default_factory=list)
    retry_policy: Optional['RetryPolicy'] = None
    timeout_seconds: float = 300.0
    condition: Optional[Callable[[Dict], bool]] = None  # 条件执行
    fan_out: bool = False                    # 扇出（并行）
    fan_in: bool = False                     # 扇入（汇聚）
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryPolicy:
    """重试策略"""
    max_retries: int = 3
    delay_seconds: float = 1.0
    exponential_backoff: bool = True
    max_delay_seconds: float = 60.0
    retry_on: List[type] = field(default_factory=lambda: [Exception])


@dataclass
class NodeState:
    """节点运行时状态"""
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    attempt_history: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class WorkflowState:
    """工作流运行时状态"""
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    nodes: Dict[str, NodeState] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    current_node: Optional[str] = None
    checkpoint_id: Optional[str] = None

    @property
    def progress(self) -> float:
        if not self.nodes:
            return 0.0
        completed = sum(1 for n in self.nodes.values()
                       if n.status in (NodeStatus.COMPLETED, NodeStatus.SKIPPED))
        return (completed / len(self.nodes)) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_node": self.current_node,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "checkpoint_id": self.checkpoint_id,
        }


class WorkflowGraph:
    """
    工作流图定义

    使用类装饰器模式定义DAG：

    @workflow("novel_generation")
    class NovelGenerationWorkflow(WorkflowGraph):
        def define(self):
            self.add_node("director", agent="DirectorAgent")
            self.add_node("plot_manager", agent="PlotManagerAgent")
            self.add_node("world_state", agent="WorldStateAgent")
            self.add_node("character_mind", agent="CharacterMindAgent", fan_out=True)
            self.add_node("event_sim", agent="EventSimulatorAgent")
            self.add_node("scene_writer", agent="SceneWriterAgent", fan_out=True)
            self.add_node("dialogue_writer", agent="DialogueWriterAgent")
            self.add_node("style_enforcer", agent="StyleEnforcerAgent")
            self.add_node("quality_gate", agent="ConsistencyCheckerAgent")

            # 定义边
            self.add_edge("director", "plot_manager")
            self.add_edge("plot_manager", "world_state")
            self.add_edge("world_state", "character_mind")
            self.add_edge("character_mind", "event_sim")
            self.add_edge("event_sim", "scene_writer")
            self.add_edge("scene_writer", "dialogue_writer")
            self.add_edge("dialogue_writer", "style_enforcer")
            self.add_edge("style_enforcer", "quality_gate")

            # 条件分支：质量检查失败则重试
            self.add_conditional_edge(
                "quality_gate",
                condition=lambda state: state.get("quality.passed", False),
                true_target="completed",
                false_target="scene_writer"
            )
    """

    def __init__(self, name: str):
        self.name = name
        self._nodes: Dict[str, NodeDefinition] = {}
        self._edges: List[tuple] = []                    # (from, to)
        self._conditional_edges: List[Dict] = []         # 条件边
        self._compiled = False

    def add_node(
        self,
        node_id: str,
        agent: str,
        dependencies: List[str] = None,
        retry: RetryPolicy = None,
        timeout: float = 300.0,
        condition: Callable = None,
        fan_out: bool = False,
        fan_in: bool = False,
        **metadata
    ) -> 'WorkflowGraph':
        """添加节点（支持链式调用）"""
        self._nodes[node_id] = NodeDefinition(
            node_id=node_id,
            agent_name=agent,
            process_func=None,  # 运行时绑定
            dependencies=dependencies or [],
            retry_policy=retry or RetryPolicy(),
            timeout_seconds=timeout,
            condition=condition,
            fan_out=fan_out,
            fan_in=fan_in,
            metadata=metadata
        )
        return self

    def add_edge(self, from_node: str, to_node: str) -> 'WorkflowGraph':
        """添加边"""
        self._edges.append((from_node, to_node))
        return self

    def add_conditional_edge(
        self,
        from_node: str,
        condition: Callable[[Dict], bool],
        true_target: str,
        false_target: str
    ) -> 'WorkflowGraph':
        """添加条件边"""
        self._conditional_edges.append({
            "from": from_node,
            "condition": condition,
            "true": true_target,
            "false": false_target
        })
        return self

    def get_ready_nodes(self, workflow_state: WorkflowState) -> List[str]:
        """获取就绪节点（所有依赖已完成）"""
        ready = []
        for node_id, node_def in self._nodes.items():
            node_state = workflow_state.nodes.get(node_id)
            if not node_state or node_state.status != NodeStatus.PENDING:
                continue

            # 检查条件
            if node_def.condition and not node_def.condition(workflow_state.shared_state):
                node_state.status = NodeStatus.SKIPPED
                continue

            # 检查依赖
            all_deps_done = all(
                workflow_state.nodes.get(dep, NodeState(dep)).status
                in (NodeStatus.COMPLETED, NodeStatus.SKIPPED)
                for dep in node_def.dependencies
            )
            if all_deps_done:
                ready.append(node_id)

        return ready

    def compile(self) -> 'CompiledWorkflow':
        """编译工作流"""
        # 拓扑排序验证
        self._validate_acyclic()
        self._compiled = True
        return CompiledWorkflow(self)

    def _validate_acyclic(self):
        """验证无环"""
        visited = set()
        rec_stack = set()

        def dfs(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)
            for from_n, to_n in self._edges:
                if from_n == node_id:
                    if to_n not in visited:
                        if dfs(to_n):
                            return True
                    elif to_n in rec_stack:
                        raise ValueError(f"Cycle detected in workflow: {node_id} -> {to_n}")
            rec_stack.remove(node_id)
            return False

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于前端可视化）"""
        return {
            "name": self.name,
            "nodes": [
                {
                    "id": n.node_id,
                    "agent": n.agent_name,
                    "dependencies": n.dependencies,
                    "fan_out": n.fan_out,
                    "fan_in": n.fan_in,
                    "metadata": n.metadata
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {"from": f, "to": t} for f, t in self._edges
            ],
            "conditional_edges": self._conditional_edges
        }


class CompiledWorkflow:
    """编译后的工作流（可执行）"""

    def __init__(self, graph: WorkflowGraph):
        self.graph = graph
        self._agent_registry: Dict[str, Any] = {}  # agent_name -> Agent实例

    def register_agent(self, agent_name: str, agent_instance: Any):
        """注册Agent实例"""
        self._agent_registry[agent_name] = agent_instance
        # 绑定process_func
        for node in self.graph._nodes.values():
            if node.agent_name == agent_name:
                node.process_func = agent_instance.process

    def create_instance(self, workflow_id: Optional[str] = None) -> WorkflowState:
        """创建工作流实例"""
        wf_id = workflow_id or f"wf_{uuid.uuid4().hex[:12]}"
        state = WorkflowState(
            workflow_id=wf_id,
            workflow_name=self.graph.name
        )
        # 初始化所有节点状态
        for node_id in self.graph._nodes:
            state.nodes[node_id] = NodeState(node_id=node_id)
        return state


class TaskOrchestrator:
    """
    任务编排引擎（原WorkflowEngine）

    核心职责：
    1. 管理已编译工作流的注册表
    2. 执行工作流实例（异步）
    3. 管理并发控制
    4. 发布执行事件到EventBus
    5. 集成CheckpointManager
    """

    def __init__(
        self,
        max_concurrent_nodes: int = 5,
        event_bus: Optional[EventBus] = None,
        checkpoint_manager: Optional['CheckpointManager'] = None
    ):
        self._workflows: Dict[str, CompiledWorkflow] = {}
        self._running_instances: Dict[str, WorkflowState] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_nodes)
        self._event_bus = event_bus or EventBus()
        self._checkpoint_manager = checkpoint_manager
        self._metrics = MetricsCollector()
        self._logger = get_logger()

    def register_workflow(self, workflow: CompiledWorkflow) -> str:
        """注册工作流模板"""
        name = workflow.graph.name
        self._workflows[name] = workflow
        self._logger.info(f"Workflow registered: {name}")
        return name

    async def execute(
        self,
        workflow_name: str,
        initial_state: Dict[str, Any],
        workflow_id: Optional[str] = None
    ) -> WorkflowState:
        """
        执行工作流

        Args:
            workflow_name: 工作流名称
            initial_state: 初始共享状态
            workflow_id: 可选的自定义工作流ID

        Returns:
            最终工作流状态
        """
        compiled = self._workflows.get(workflow_name)
        if not compiled:
            raise ValueError(f"Workflow not found: {workflow_name}")

        # 创建工作流实例
        wf_state = compiled.create_instance(workflow_id)
        wf_state.shared_state.update(initial_state)
        wf_state.status = WorkflowStatus.RUNNING
        wf_state.started_at = time.time()
        self._running_instances[wf_state.workflow_id] = wf_state

        # 发布开始事件
        await self._publish_event(EventType.TASK_STARTED, wf_state)

        try:
            while wf_state.status == WorkflowStatus.RUNNING:
                # 获取就绪节点
                ready_nodes = compiled.graph.get_ready_nodes(wf_state)

                if not ready_nodes:
                    # 检查是否全部完成
                    all_done = all(
                        n.status in (NodeStatus.COMPLETED, NodeStatus.SKIPPED, NodeStatus.FAILED, NodeStatus.CANCELLED)
                        for n in wf_state.nodes.values()
                    )
                    if all_done:
                        # 检查是否有失败
                        has_failed = any(n.status == NodeStatus.FAILED for n in wf_state.nodes.values())
                        wf_state.status = WorkflowStatus.FAILED if has_failed else WorkflowStatus.COMPLETED
                        wf_state.completed_at = time.time()
                        break
                    else:
                        # 等待其他节点完成
                        await asyncio.sleep(0.1)
                        continue

                # 并行执行就绪节点（受信号量限制）
                tasks = []
                for node_id in ready_nodes:
                    task = self._execute_node(compiled, wf_state, node_id)
                    tasks.append(task)

                await asyncio.gather(*tasks, return_exceptions=True)

                # 自动checkpoint（每完成一个批次）
                if self._checkpoint_manager:
                    await self._checkpoint_manager.save(wf_state)

            # 发布完成事件
            event_type = (
                EventType.TASK_COMPLETED if wf_state.status == WorkflowStatus.COMPLETED
                else EventType.TASK_FAILED
            )
            await self._publish_event(event_type, wf_state)

        except asyncio.CancelledError:
            wf_state.status = WorkflowStatus.CANCELLED
            await self._publish_event(EventType.TASK_CANCELLED, wf_state)
            raise

        finally:
            if wf_state.workflow_id in self._running_instances:
                del self._running_instances[wf_state.workflow_id]

        return wf_state

    async def _execute_node(
        self,
        compiled: CompiledWorkflow,
        wf_state: WorkflowState,
        node_id: str
    ):
        """执行单个节点"""
        async with self._semaphore:
            node_def = compiled.graph._nodes[node_id]
            node_state = wf_state.nodes[node_id]

            node_state.status = NodeStatus.RUNNING
            node_state.started_at = time.time()
            wf_state.current_node = node_id

            # 发布节点开始事件
            await self._publish_node_event("node_started", wf_state, node_state)

            try:
                # 获取Agent实例
                agent = compiled._agent_registry.get(node_def.agent_name)
                if not agent:
                    raise RuntimeError(f"Agent not registered: {node_def.agent_name}")

                # 执行（带超时）
                result = await asyncio.wait_for(
                    self._invoke_agent(agent, wf_state.shared_state),
                    timeout=node_def.timeout_seconds
                )

                node_state.result = result
                node_state.status = NodeStatus.COMPLETED

                # 更新共享状态（Agent返回的增量更新）
                if isinstance(result, dict):
                    wf_state.shared_state.update(result)

            except asyncio.TimeoutError:
                node_state.error = f"Timeout after {node_def.timeout_seconds}s"
                node_state.status = NodeStatus.FAILED
                await self._handle_node_failure(node_def, node_state)

            except Exception as e:
                node_state.error = str(e)
                node_state.status = NodeStatus.FAILED
                await self._handle_node_failure(node_def, node_state)

            finally:
                node_state.completed_at = time.time()
                node_state.duration_ms = (
                    (node_state.completed_at - node_state.started_at) * 1000
                    if node_state.started_at else 0
                )

                # 发布节点完成事件
                await self._publish_node_event(
                    "node_completed" if node_state.status == NodeStatus.COMPLETED else "node_failed",
                    wf_state, node_state
                )

                # 记录指标
                self._metrics.record_histogram(
                    "node_execution_duration_ms",
                    node_state.duration_ms,
                    {"agent": node_def.agent_name, "status": node_state.status.value}
                )

    async def _invoke_agent(self, agent: Any, shared_state: Dict) -> Any:
        """调用Agent处理函数"""
        if asyncio.iscoroutinefunction(agent.process):
            return await agent.process(shared_state)
        else:
            # 同步函数在线程池执行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, agent.process, shared_state)

    async def _handle_node_failure(self, node_def: NodeDefinition, node_state: NodeState):
        """处理节点失败（重试逻辑）"""
        retry_policy = node_def.retry_policy
        if retry_policy and node_state.retry_count < retry_policy.max_retries:
            node_state.retry_count += 1
            node_state.status = NodeStatus.RETRYING

            delay = retry_policy.delay_seconds
            if retry_policy.exponential_backoff:
                delay = min(delay * (2 ** (node_state.retry_count - 1)),
                           retry_policy.max_delay_seconds)

            self._logger.warning(
                f"Node {node_state.node_id} failed, retrying ({node_state.retry_count}/{retry_policy.max_retries}) "
                f"after {delay}s"
            )
            await asyncio.sleep(delay)
            node_state.status = NodeStatus.PENDING  # 重新排队

    async def _publish_event(self, event_type: EventType, wf_state: WorkflowState):
        """发布工作流级事件"""
        await self._event_bus.publish_type(
            event_type,
            payload={
                "workflow_id": wf_state.workflow_id,
                "workflow_name": wf_state.workflow_name,
                "status": wf_state.status.value,
                "progress": wf_state.progress,
                "current_node": wf_state.current_node,
            },
            source="workflow_engine",
            correlation_id=wf_state.workflow_id
        )

    async def _publish_node_event(self, event_subtype: str, wf_state: WorkflowState, node_state: NodeState):
        """发布节点级事件"""
        await self._event_bus.publish_type(
            f"workflow.{event_subtype}",
            payload={
                "workflow_id": wf_state.workflow_id,
                "node_id": node_state.node_id,
                "status": node_state.status.value,
                "duration_ms": node_state.duration_ms,
                "error": node_state.error,
            },
            source="workflow_engine",
            correlation_id=wf_state.workflow_id,
            priority=EventPriority.HIGH if node_state.status == NodeStatus.FAILED else EventPriority.NORMAL
        )

    def get_instance(self, workflow_id: str) -> Optional[WorkflowState]:
        """获取运行中的工作流实例"""
        return self._running_instances.get(workflow_id)

    async def cancel(self, workflow_id: str) -> bool:
        """取消工作流"""
        wf_state = self._running_instances.get(workflow_id)
        if not wf_state:
            return False
        wf_state.status = WorkflowStatus.CANCELLED
        return True

    def list_running(self) -> List[WorkflowState]:
        """列出运行中的工作流"""
        return list(self._running_instances.values())
```

### 4.2 TaskScheduler - 任务调度器

**职责**: 任务队列管理、优先级调度、资源限制、延迟执行、定时任务

**参考**: Celery + Prefect Scheduler + Kubernetes CronJob

**实现模板**:

```python
# src/deepnovel/scheduling/task_scheduler.py

from typing import Any, Dict, List, Optional, Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import time
import uuid
import heapq
from collections import deque

from src.deepnovel.core.event_bus import EventBus, EventType, EventPriority
from src.deepnovel.utils import get_logger

logger = get_logger()


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskState(Enum):
    """任务状态"""
    PENDING = "pending"          # 等待调度
    SCHEDULED = "scheduled"      # 已安排执行时间
    QUEUED = "queued"            # 在队列中等待
    RUNNING = "running"          # 正在执行
    PAUSED = "paused"            # 暂停
    COMPLETED = "completed"      # 完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 取消
    TIMEOUT = "timeout"          # 超时
    RETRYING = "retrying"        # 重试中


@dataclass(order=True)
class ScheduledTask:
    """可调度的任务"""
    # heapq按第一个字段排序，使用元组 (priority, scheduled_time, task_id)
    sort_key: tuple = field(compare=True)
    task_id: str = field(compare=False)
    workflow_name: str = field(compare=False)
    initial_state: Dict[str, Any] = field(compare=False, default_factory=dict)
    priority: TaskPriority = field(compare=False, default=TaskPriority.NORMAL)
    scheduled_time: float = field(compare=False, default_factory=time.time)
    created_at: float = field(compare=False, default_factory=time.time)
    max_retries: int = field(compare=False, default=3)
    retry_count: int = field(compare=False, default=0)
    timeout_seconds: float = field(compare=False, default=3600.0)
    user_id: Optional[str] = field(compare=False, default=None)
    metadata: Dict[str, Any] = field(compare=False, default_factory=dict)
    state: TaskState = field(compare=False, default=TaskState.PENDING)
    started_at: Optional[float] = field(compare=False, default=None)
    completed_at: Optional[float] = field(compare=False, default=None)
    error_message: Optional[str] = field(compare=False, default=None)
    workflow_instance_id: Optional[str] = field(compare=False, default=None)

    def __post_init__(self):
        if self.sort_key is None:
            self.sort_key = (self.priority.value, self.scheduled_time, self.task_id)


class TaskScheduler:
    """
    任务调度器

    核心功能：
    1. 优先级任务队列（最小堆）
    2. 延迟调度（支持未来时间点执行）
    3. 并发控制（资源限制）
    4. 定时任务（Cron-like）
    5. 任务持久化（SQLite）
    6. 背压机制（队列满时拒绝或降级）

    参考：Celery + Prefect Scheduler
    """

    def __init__(
        self,
        task_orchestrator: 'TaskOrchestrator',
        max_concurrent_tasks: int = 3,
        max_queue_size: int = 100,
        default_timeout: float = 3600.0,
        persistence: Optional['TaskPersistence'] = None,
        event_bus: Optional[EventBus] = None
    ):
        self._workflow_engine = workflow_engine
        self._max_concurrent = max_concurrent_tasks
        self._max_queue_size = max_queue_size
        self._default_timeout = default_timeout
        self._persistence = persistence
        self._event_bus = event_bus or EventBus()

        # 任务队列（最小堆）
        self._queue: List[ScheduledTask] = []
        self._queue_lock = asyncio.Lock()

        # 运行中任务
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._running_semaphore = asyncio.Semaphore(max_concurrent_tasks)

        # 定时任务
        self._cron_tasks: Dict[str, 'CronEntry'] = {}
        self._cron_task: Optional[asyncio.Task] = None

        # 状态追踪
        self._task_history: deque = deque(maxlen=1000)
        self._shutdown_event = asyncio.Event()
        self._logger = get_logger()

    async def submit(
        self,
        workflow_name: str,
        initial_state: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: float = 0.0,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **metadata
    ) -> str:
        """
        提交任务到调度队列

        Args:
            workflow_name: 工作流名称
            initial_state: 初始状态
            priority: 优先级
            delay_seconds: 延迟执行秒数
            task_id: 自定义任务ID
            user_id: 用户ID

        Returns:
            task_id
        """
        tid = task_id or f"task_{uuid.uuid4().hex[:16]}"
        scheduled_time = time.time() + delay_seconds

        task = ScheduledTask(
            sort_key=(priority.value, scheduled_time, tid),
            task_id=tid,
            workflow_name=workflow_name,
            initial_state=initial_state,
            priority=priority,
            scheduled_time=scheduled_time,
            user_id=user_id,
            metadata=metadata
        )

        async with self._queue_lock:
            # 背压检查
            if len(self._queue) >= self._max_queue_size:
                raise RuntimeError(f"Task queue full (max={self._max_queue_size})")

            heapq.heappush(self._queue, task)

        # 持久化
        if self._persistence:
            await self._persistence.save_task(task)

        # 发布事件
        await self._event_bus.publish_type(
            EventType.TASK_CREATED,
            payload={
                "task_id": tid,
                "workflow_name": workflow_name,
                "priority": priority.value,
                "scheduled_time": scheduled_time,
                "user_id": user_id
            },
            source="task_scheduler"
        )

        self._logger.info(f"Task submitted: {tid} (workflow={workflow_name}, priority={priority.name})")
        return tid

    async def start(self):
        """启动调度器"""
        self._logger.info("Task scheduler started")

        # 恢复持久化任务
        if self._persistence:
            await self._restore_tasks()

        # 启动调度循环
        asyncio.create_task(self._scheduler_loop())

        # 启动定时任务扫描
        self._cron_task = asyncio.create_task(self._cron_loop())

    async def _scheduler_loop(self):
        """调度主循环"""
        while not self._shutdown_event.is_set():
            try:
                now = time.time()
                ready_tasks = []

                async with self._queue_lock:
                    # 提取到期的就绪任务
                    while self._queue:
                        task = self._queue[0]
                        if task.scheduled_time <= now and task.state == TaskState.PENDING:
                            heapq.heappop(self._queue)
                            task.state = TaskState.QUEUED
                            ready_tasks.append(task)
                        else:
                            break

                # 执行就绪任务
                for task in ready_tasks:
                    asyncio.create_task(self._execute_task(task))

                # 等待一小段时间
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=0.5
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task: ScheduledTask):
        """执行任务"""
        async with self._running_semaphore:
            task.state = TaskState.RUNNING
            task.started_at = time.time()

            # 持久化状态更新
            if self._persistence:
                await self._persistence.update_task(task)

            # 发布开始事件
            await self._event_bus.publish_type(
                EventType.TASK_STARTED,
                payload={"task_id": task.task_id, "workflow_name": task.workflow_name},
                source="task_scheduler",
                correlation_id=task.task_id
            )

            try:
                # 执行工作流
                workflow_state = await asyncio.wait_for(
                    self._workflow_engine.execute(
                        task.workflow_name,
                        task.initial_state,
                        workflow_id=task.task_id
                    ),
                    timeout=task.timeout_seconds
                )

                task.state = TaskState.COMPLETED
                task.workflow_instance_id = workflow_state.workflow_id
                task.completed_at = time.time()

                # 发布完成事件
                await self._event_bus.publish_type(
                    EventType.TASK_COMPLETED,
                    payload={
                        "task_id": task.task_id,
                        "workflow_id": workflow_state.workflow_id,
                        "duration": task.completed_at - task.started_at
                    },
                    source="task_scheduler",
                    correlation_id=task.task_id
                )

            except asyncio.TimeoutError:
                task.state = TaskState.TIMEOUT
                task.error_message = f"Timeout after {task.timeout_seconds}s"
                await self._handle_task_failure(task)

            except Exception as e:
                task.state = TaskState.FAILED
                task.error_message = str(e)
                await self._handle_task_failure(task)

            finally:
                self._task_history.append(task)
                if self._persistence:
                    await self._persistence.update_task(task)

                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]

    async def _handle_task_failure(self, task: ScheduledTask):
        """处理任务失败"""
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.state = TaskState.RETRYING
            delay = 2 ** task.retry_count  # 指数退避

            self._logger.warning(
                f"Task {task.task_id} failed, retrying ({task.retry_count}/{task.max_retries})"
            )

            # 重新入队
            task.scheduled_time = time.time() + delay
            task.sort_key = (task.priority.value, task.scheduled_time, task.task_id)

            async with self._queue_lock:
                heapq.heappush(self._queue, task)
        else:
            # 最终失败
            await self._event_bus.publish_type(
                EventType.TASK_FAILED,
                payload={
                    "task_id": task.task_id,
                    "error": task.error_message,
                    "retry_count": task.retry_count
                },
                source="task_scheduler",
                correlation_id=task.task_id,
                priority=EventPriority.HIGH
            )

    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        # 检查运行中任务
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            return True

        # 检查队列
        async with self._queue_lock:
            for task in self._queue:
                if task.task_id == task_id:
                    task.state = TaskState.CANCELLED
                    self._queue.remove(task)
                    heapq.heapify(self._queue)
                    return True

        return False

    async def pause(self, task_id: str) -> bool:
        """暂停任务（仅支持运行中的TaskOrchestrator级暂停）"""
        return await self._workflow_engine.cancel(task_id)

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务信息"""
        # 检查队列
        for task in self._queue:
            if task.task_id == task_id:
                return task
        # 检查历史
        for task in self._task_history:
            if task.task_id == task_id:
                return task
        return None

    def list_tasks(
        self,
        status: Optional[TaskState] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ScheduledTask]:
        """列出任务"""
        all_tasks = list(self._queue) + list(self._task_history)

        if status:
            all_tasks = [t for t in all_tasks if t.state == status]
        if user_id:
            all_tasks = [t for t in all_tasks if t.user_id == user_id]

        return sorted(all_tasks, key=lambda t: t.created_at, reverse=True)[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计"""
        return {
            "queue_size": len(self._queue),
            "running_count": len(self._running_tasks),
            "max_concurrent": self._max_concurrent,
            "history_size": len(self._task_history),
            "queue_capacity": self._max_queue_size,
            "utilization": len(self._running_tasks) / self._max_concurrent if self._max_concurrent > 0 else 0
        }

    async def shutdown(self):
        """关闭调度器"""
        self._shutdown_event.set()

        # 取消所有运行中任务
        for task in self._running_tasks.values():
            task.cancel()

        if self._cron_task:
            self._cron_task.cancel()

        self._logger.info("Task scheduler shutdown")

    # ---- 定时任务支持 ----

    async def schedule_cron(
        self,
        name: str,
        workflow_name: str,
        cron_expression: str,  # "*/5 * * * *" (分 时 日 月 周)
        initial_state: Dict[str, Any] = None,
        **metadata
    ):
        """添加定时任务"""
        self._cron_tasks[name] = CronEntry(
            name=name,
            workflow_name=workflow_name,
            cron_expression=cron_expression,
            initial_state=initial_state or {},
            metadata=metadata
        )

    async def _cron_loop(self):
        """定时任务扫描循环"""
        while not self._shutdown_event.is_set():
            try:
                now = datetime.now()
                for entry in self._cron_tasks.values():
                    if entry.should_run(now):
                        await self.submit(
                            workflow_name=entry.workflow_name,
                            initial_state=entry.initial_state,
                            priority=TaskPriority.BACKGROUND,
                            **entry.metadata
                        )
                        entry.last_run = now

                await asyncio.sleep(60)  # 每分钟检查
            except Exception as e:
                self._logger.error(f"Cron loop error: {e}")
                await asyncio.sleep(60)

    async def _restore_tasks(self):
        """从持久化恢复任务"""
        if not self._persistence:
            return

        tasks = await self._persistence.load_pending_tasks()
        async with self._queue_lock:
            for task in tasks:
                heapq.heappush(self._queue, task)

        self._logger.info(f"Restored {len(tasks)} tasks from persistence")


@dataclass
class CronEntry:
    """定时任务条目"""
    name: str
    workflow_name: str
    cron_expression: str
    initial_state: Dict[str, Any]
    metadata: Dict[str, Any]
    last_run: Optional[datetime] = None

    def should_run(self, now: datetime) -> bool:
        """检查是否应该执行（简化实现）"""
        # 使用 croniter 或类似库解析 cron 表达式
        # 这里为占位实现
        if self.last_run is None:
            return True
        # TODO: 实现 cron 表达式解析
        return False
```

### 4.3 CheckpointManager - 断点管理器

**职责**: 工作流状态持久化、断点恢复、版本管理

**参考**: Temporal History + LangGraph Checkpointer

```python
# src/deepnovel/scheduling/checkpoint.py

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import json
import time
import sqlite3
from pathlib import Path

from src.deepnovel.utils import get_logger

logger = get_logger()


class CheckpointManager:
    """
    断点管理器

    核心功能：
    1. 自动保存工作流状态（按节点完成批次）
    2. 从断点恢复工作流
    3. 历史版本管理
    4. 压缩/清理旧checkpoint

    存储策略：
    - SQLite: 元数据 + 状态索引
    - 文件系统: 大状态对象（JSON文件）
    """

    def __init__(self, db_path: str = "data/checkpoints.db", state_dir: str = "data/checkpoints"):
        self._db_path = db_path
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    workflow_name TEXT,
                    checkpoint_id TEXT UNIQUE NOT NULL,
                    node_count INTEGER,
                    completed_nodes INTEGER,
                    progress REAL,
                    state_file TEXT,
                    created_at REAL,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow ON checkpoints(workflow_id)
            """)
            conn.commit()

    async def save(self, workflow_state: 'WorkflowState') -> str:
        """保存checkpoint"""
        checkpoint_id = f"cp_{int(time.time() * 1000)}"
        state_file = self._state_dir / f"{checkpoint_id}.json"

        # 序列化状态
        state_data = workflow_state.to_dict()

        # 写入文件
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, default=str)

        # 写入数据库索引
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT INTO checkpoints
                (workflow_id, workflow_name, checkpoint_id, node_count, completed_nodes, progress, state_file, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow_state.workflow_id,
                workflow_state.workflow_name,
                checkpoint_id,
                len(workflow_state.nodes),
                sum(1 for n in workflow_state.nodes.values() if n.status.value == "completed"),
                workflow_state.progress,
                str(state_file),
                time.time()
            ))
            conn.commit()

        workflow_state.checkpoint_id = checkpoint_id
        logger.info(f"Checkpoint saved: {checkpoint_id} (progress={workflow_state.progress:.1f}%)")
        return checkpoint_id

    async def load(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """加载最新的checkpoint"""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT state_file FROM checkpoints
                WHERE workflow_id = ? AND is_active = 1
                ORDER BY created_at DESC LIMIT 1
            """, (workflow_id,))
            row = cursor.fetchone()

        if not row:
            return None

        state_file = Path(row[0])
        if not state_file.exists():
            return None

        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def list_checkpoints(self, workflow_id: str) -> List[Dict]:
        """列出工作流的所有checkpoint"""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT checkpoint_id, node_count, completed_nodes, progress, created_at
                FROM checkpoints
                WHERE workflow_id = ?
                ORDER BY created_at DESC
            """, (workflow_id,))
            rows = cursor.fetchall()

        return [
            {
                "checkpoint_id": r[0],
                "node_count": r[1],
                "completed_nodes": r[2],
                "progress": r[3],
                "created_at": r[4]
            }
            for r in rows
        ]

    async def cleanup(self, workflow_id: str, keep_last: int = 5):
        """清理旧checkpoint，只保留最近N个"""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT checkpoint_id, state_file FROM checkpoints
                WHERE workflow_id = ?
                ORDER BY created_at DESC
            """, (workflow_id,))
            rows = cursor.fetchall()

            to_delete = rows[keep_last:]
            for checkpoint_id, state_file in to_delete:
                # 删除文件
                Path(state_file).unlink(missing_ok=True)
                # 标记为非活跃
                conn.execute(
                    "UPDATE checkpoints SET is_active = 0 WHERE checkpoint_id = ?",
                    (checkpoint_id,)
                )

            conn.commit()
            logger.info(f"Cleaned up {len(to_delete)} old checkpoints for {workflow_id}")
```

### 4.4 EventStore - 事件持久化

**职责**: 事件时序存储、查询、回放

```python
# src/deepnovel/scheduling/event_store.py

import sqlite3
import json
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from src.deepnovel.core.event_bus import Event


class EventStore:
    """
    事件存储

    使用SQLite时序表存储所有事件，支持：
    1. 按workflow_id查询事件历史
    2. 按时间范围查询
    3. 事件回放（用于调试和可视化重放）
    4. 事件统计聚合
    """

    def __init__(self, db_path: str = "data/events.db"):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT,
                    correlation_id TEXT,
                    workflow_id TEXT,
                    task_id TEXT,
                    node_id TEXT,
                    payload TEXT,
                    priority INTEGER,
                    timestamp REAL,
                    created_at REAL DEFAULT (unixepoch())
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_correlation ON events(correlation_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow ON events(workflow_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)
            """)
            conn.commit()

    async def append(self, event: Event):
        """追加事件"""
        payload = event.payload if isinstance(event.payload, str) else json.dumps(event.payload, ensure_ascii=False)

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO events
                (event_id, event_type, source, correlation_id, workflow_id, task_id, node_id, payload, priority, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.type,
                event.source,
                event.correlation_id,
                event.payload.get("workflow_id") if isinstance(event.payload, dict) else None,
                event.payload.get("task_id") if isinstance(event.payload, dict) else None,
                event.payload.get("node_id") if isinstance(event.payload, dict) else None,
                payload,
                event.priority.value if hasattr(event.priority, 'value') else event.priority,
                event.timestamp
            ))
            conn.commit()

    async def query(
        self,
        workflow_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """查询事件"""
        conditions = []
        params = []

        if workflow_id:
            conditions.append("workflow_id = ?")
            params.append(workflow_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT * FROM events {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])
            rows = cursor.fetchall()

        return [dict(r) for r in rows]

    async def get_workflow_timeline(self, workflow_id: str) -> List[Dict]:
        """获取工作流完整时间线（用于可视化）"""
        return await self.query(workflow_id=workflow_id, limit=1000)

    async def get_stats(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流事件统计"""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    event_type,
                    COUNT(*) as count,
                    MIN(timestamp) as first_occurrence,
                    MAX(timestamp) as last_occurrence
                FROM events
                WHERE workflow_id = ?
                GROUP BY event_type
            """, (workflow_id,))
            rows = cursor.fetchall()

        return {
            r[0]: {
                "count": r[1],
                "first": r[2],
                "last": r[3]
            }
            for r in rows
        }
```

### 4.5 MetricsCollector - 指标采集器（重构PerformanceMonitor）

```python
# src/deepnovel/scheduling/metrics.py

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    指标采集器

    增强版性能监控，支持：
    1. 实时指标流（供可视化使用）
    2. 指标聚合（窗口统计）
    3. 指标导出（Prometheus格式）
    4. 告警规则（阈值触发）
    """

    def __init__(self, max_history: int = 10000):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, Dict] = {}

        # 历史数据（时序）
        self._time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))

        self._lock = threading.RLock()
        self._alert_handlers: List[Callable] = []
        self._thresholds: Dict[str, Dict] = {}

    def record_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """记录计数器"""
        with self._lock:
            self._counters[name] += value
            point = MetricPoint(name, self._counters[name], time.time(), labels or {})
            self._time_series[name].append(point)
            self._check_threshold(name, self._counters[name])

    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录仪表盘值"""
        with self._lock:
            self._gauges[name] = value
            point = MetricPoint(name, value, time.time(), labels or {})
            self._time_series[name].append(point)
            self._check_threshold(name, value)

    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录直方图值"""
        with self._lock:
            self._histograms[name].append(value)
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-1000:]
            point = MetricPoint(name, value, time.time(), labels or {})
            self._time_series[name].append(point)

    def start_timer(self, name: str, labels: Dict[str, str] = None) -> str:
        """开始计时"""
        timer_id = f"{name}_{time.time()}"
        with self._lock:
            self._timers[timer_id] = {"name": name, "start": time.time(), "labels": labels or {}}
        return timer_id

    def stop_timer(self, timer_id: str) -> Optional[float]:
        """停止计时"""
        with self._lock:
            if timer_id not in self._timers:
                return None
            timer = self._timers.pop(timer_id)
            duration_ms = (time.time() - timer["start"]) * 1000
            self.record_histogram(timer["name"], duration_ms, timer["labels"])
            return duration_ms

    def get_time_series(
        self,
        name: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 1000
    ) -> List[MetricPoint]:
        """获取时序数据（供可视化图表使用）"""
        with self._lock:
            series = list(self._time_series.get(name, []))

        if start_time:
            series = [p for p in series if p.timestamp >= start_time]
        if end_time:
            series = [p for p in series if p.timestamp <= end_time]

        return series[-limit:]

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """获取直方图统计"""
        with self._lock:
            values = self._histograms.get(name, [])
            if not values:
                return {}
            sorted_values = sorted(values)
            n = len(sorted_values)
            return {
                "count": n,
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "mean": sum(values) / n,
                "p50": sorted_values[int(n * 0.5)],
                "p90": sorted_values[int(n * 0.9)],
                "p95": sorted_values[int(n * 0.95)],
                "p99": sorted_values[int(n * 0.99)] if n >= 100 else sorted_values[-1]
            }

    def export_prometheus(self) -> str:
        """导出Prometheus格式指标"""
        lines = []

        with self._lock:
            # Counters
            for name, value in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value}")

            # Gauges
            for name, value in self._gauges.items():
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {value}")

            # Histograms
            for name, values in self._histograms.items():
                stats = self.get_histogram_stats(name)
                if stats:
                    lines.append(f"# TYPE {name} histogram")
                    lines.append(f'{name}_bucket{{le="+Inf"}} {stats["count"]}')
                    lines.append(f'{name}_sum {sum(values)}')
                    lines.append(f'{name}_count {stats["count"]}')

        return "\n".join(lines)

    def set_threshold(self, name: str, min_val: float = None, max_val: float = None):
        """设置告警阈值"""
        self._thresholds[name] = {"min": min_val, "max": max_val}

    def _check_threshold(self, name: str, value: float):
        """检查阈值"""
        threshold = self._thresholds.get(name)
        if not threshold:
            return

        if threshold.get("max") is not None and value > threshold["max"]:
            for handler in self._alert_handlers:
                handler(name, "above_threshold", value, threshold["max"])

        if threshold.get("min") is not None and value < threshold["min"]:
            for handler in self._alert_handlers:
                handler(name, "below_threshold", value, threshold["min"])

    def on_alert(self, handler: Callable):
        """注册告警处理器"""
        self._alert_handlers.append(handler)

    def get_snapshot(self) -> Dict[str, Any]:
        """获取指标快照（供API和可视化使用）"""
        with self._lock:
            return {
                "timestamp": time.time(),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: self.get_histogram_stats(name)
                    for name in self._histograms.keys()
                }
            }
```

---

## 5. 可视化层设计

### 5.1 可视化架构

```
前端 (Vue3 + Element Plus + D3.js)
    │
    ├── WebSocket Connection ───→ FastAPI WebSocket Endpoint
    │                              (实时事件推送)
    │
    ├── SSE Stream ─────────────→ /tasks/{id}/stream
    │                              (任务日志流)
    │
    └── REST API ───────────────→ /tasks, /workflows, /metrics
                                   (初始数据和配置)
```

### 5.2 新增前端视图

#### 5.2.1 WorkflowGraphView - 交互式DAG图

**功能**:
- D3.js力导向图渲染工作流DAG
- 节点实时着色（pending/running/completed/failed）
- 点击节点查看详细执行信息
- 拖拽调整布局
- 缩放/平移
- 边动画（数据流方向）

```vue
<!-- frontend/src/views/WorkflowGraphView.vue -->
<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as d3 from 'd3'
import { useWebSocket } from '@/composables/useWebSocket'

interface GraphNode {
  id: string
  agent: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  x?: number
  y?: number
  fx?: number
  fy?: number
}

interface GraphEdge {
  source: string | GraphNode
  target: string | GraphNode
  animated?: boolean
}

const props = defineProps<{
  workflowId: string
}>()

const svgRef = ref<SVGSVGElement>()
const nodes = ref<GraphNode[]>([])
const edges = ref<GraphEdge[]>([])
const selectedNode = ref<GraphNode | null>(null)

// WebSocket实时更新
const { connect, disconnect, onMessage } = useWebSocket(`/ws/workflows/${props.workflowId}`)

onMessage((data) => {
  if (data.type === 'node_status_change') {
    const node = nodes.value.find(n => n.id === data.node_id)
    if (node) {
      node.status = data.status
      updateNodeColor(node)
    }
  } else if (data.type === 'workflow_progress') {
    // 更新整体进度
  }
})

function updateNodeColor(node: GraphNode) {
  const colorMap = {
    pending: '#64748b',
    running: '#06b6d4',
    completed: '#10b981',
    failed: '#ef4444',
    skipped: '#94a3b8'
  }
  d3.select(`#node-${node.id}`)
    .select('circle')
    .transition()
    .duration(300)
    .attr('fill', colorMap[node.status])
}

function renderGraph() {
  const svg = d3.select(svgRef.value)
  const width = svgRef.value!.clientWidth
  const height = svgRef.value!.clientHeight

  // 力导向模拟
  const simulation = d3.forceSimulation(nodes.value as any)
    .force('link', d3.forceLink(edges.value).id((d: any) => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))

  // 渲染边
  const link = svg.selectAll('.link')
    .data(edges.value)
    .enter().append('line')
    .attr('class', 'link')
    .attr('stroke', '#475569')
    .attr('stroke-width', 2)

  // 渲染节点
  const node = svg.selectAll('.node')
    .data(nodes.value)
    .enter().append('g')
    .attr('class', 'node')
    .attr('id', (d: any) => `node-${d.id}`)
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
    .on('click', (event: any, d: any) => {
      selectedNode.value = d
    })

  node.append('circle')
    .attr('r', 24)
    .attr('fill', (d: any) => {
      const colors: any = { pending: '#64748b', running: '#06b6d4', completed: '#10b981', failed: '#ef4444' }
      return colors[d.status] || '#64748b'
    })
    .attr('stroke', '#1e293b')
    .attr('stroke-width', 2)

  node.append('text')
    .text((d: any) => d.id)
    .attr('text-anchor', 'middle')
    .attr('dy', 4)
    .attr('fill', 'white')
    .attr('font-size', '10px')

  simulation.on('tick', () => {
    link
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y)

    node.attr('transform', (d: any) => `translate(${d.x},${d.y})`)
  })
}

onMounted(async () => {
  // 加载工作流定义
  // const definition = await api.getWorkflowDefinition(props.workflowId)
  // nodes.value = definition.nodes
  // edges.value = definition.edges
  // renderGraph()
  connect()
})

onUnmounted(() => {
  disconnect()
})
</script>

<template>
  <div class="workflow-graph-view">
    <div class="graph-container">
      <svg ref="svgRef" class="graph-svg"></svg>
    </div>
    <div v-if="selectedNode" class="node-detail-panel">
      <h3>{{ selectedNode.id }}</h3>
      <p>Agent: {{ selectedNode.agent }}</p>
      <p>Status: {{ selectedNode.status }}</p>
    </div>
  </div>
</template>
```

#### 5.2.2 ExecutionTimelineView - 执行时间线

**功能**:
- Gantt图展示各节点执行时间
- 并行执行段高亮
- 鼠标悬停显示详细耗时
- 点击跳转到对应节点日志

#### 5.2.3 RealtimeMetricsView - 实时指标面板

**功能**:
- ECharts实时折线图（任务吞吐量、节点耗时）
- 仪表盘组件（并发利用率、队列深度）
- 热力图（节点失败频率）
- 告警列表

### 5.3 后端API扩展

```python
# src/deepnovel/api/routes.py 新增端点

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

# WebSocket端点：实时工作流状态推送
@router.websocket("/ws/workflows/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    await websocket.accept()

    # 订阅事件
    async def event_handler(event):
        await websocket.send_json({
            "type": event.type,
            "payload": event.payload,
            "timestamp": event.timestamp
        })

    unsubscribe = event_bus.subscribe(f"workflow.*", event_handler)

    try:
        while True:
            # 保持连接
            data = await websocket.receive_text()
            # 可处理客户端控制命令
    except WebSocketDisconnect:
        unsubscribe()

# SSE端点：任务日志流
@router.get("/tasks/{task_id}/stream")
async def task_event_stream(task_id: str):
    async def event_generator():
        queue = asyncio.Queue()

        async def handler(event):
            if event.payload.get("task_id") == task_id:
                await queue.put(event)

        unsubscribe = event_bus.subscribe("task.*", handler)

        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(event.to_dict())}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            unsubscribe()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# 工作流定义端点
@router.get("/workflows/{workflow_name}/definition")
async def get_workflow_definition(workflow_name: str):
    """获取工作流DAG定义（供前端渲染）"""
    workflow = workflow_engine.get_workflow(workflow_name)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow.graph.to_dict()

# 工作流实时状态
@router.get("/workflows/{workflow_id}/state")
async def get_workflow_state(workflow_id: str):
    """获取工作流实时状态（包含所有节点状态）"""
    state = workflow_engine.get_instance(workflow_id)
    if not state:
        # 尝试从历史加载
        checkpoint = await checkpoint_manager.load(workflow_id)
        if checkpoint:
            return checkpoint
        raise HTTPException(status_code=404, detail="Workflow not found")
    return state.to_dict()

# 事件时间线
@router.get("/workflows/{workflow_id}/timeline")
async def get_workflow_timeline(workflow_id: str, limit: int = 500):
    """获取工作流事件时间线"""
    events = await event_store.get_workflow_timeline(workflow_id)
    return {"events": events[:limit], "total": len(events)}

# 指标端点
@router.get("/metrics")
async def get_metrics():
    """获取系统指标快照"""
    return metrics_collector.get_snapshot()

@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Prometheus格式指标导出"""
    return Response(
        content=metrics_collector.export_prometheus(),
        media_type="text/plain"
    )

# 时序数据（供图表使用）
@router.get("/metrics/timeseries/{metric_name}")
async def get_metric_timeseries(
    metric_name: str,
    start: Optional[float] = None,
    end: Optional[float] = None,
    limit: int = 1000
):
    """获取指标时序数据"""
    series = metrics_collector.get_time_series(metric_name, start, end, limit)
    return {
        "metric": metric_name,
        "data": [
            {"timestamp": p.timestamp, "value": p.value, "labels": p.labels}
            for p in series
        ]
    }
```

---

## 6. 与Step1-4的对接

### 6.1 对接Step1（数据层）

| Step1组件 | 对接方式 | 用途 |
|-----------|---------|------|
| FactManager | TaskOrchestrator节点共享状态读写 | world_state节点持久化事实 |
| EventManager | EventStore追加事件 | 模拟事件与调度事件统一存储 |
| CausalReasoningTool | causal_engine节点调用 | 因果验证作为工作流节点 |
| NarrativeRecordTool | scene_writer节点输出 | 叙事文本写入持久层 |

### 6.2 对接Step2（记忆系统）

| Step2组件 | 对接方式 | 用途 |
|-----------|---------|------|
| 三级记忆阶梯 | CharacterMindAgent节点 | 角色记忆在节点间传递 |
| MemoryManager | CheckpointManager集成 | checkpoint包含记忆状态 |

### 6.3 对接Step3（LLM层）

| Step3组件 | 对接方式 | 用途 |
|-----------|---------|------|
| LLMRouter | Agent节点process调用 | 每个Agent节点通过LLMRouter调用模型 |
| 多模型配置 | AgentConfig独立配置 | 不同节点使用不同模型 |

### 6.4 对接Step4（Agent层）

| Step4组件 | 对接方式 | 用途 |
|-----------|---------|------|
| TaskOrchestrator（原WorkflowEngine） | 本层核心实现 | 状态图执行引擎 |
| BaseAgent | 节点process函数绑定 | Agent实例注册到CompiledWorkflow |
| DirectorAgent | 特殊节点（入口） | 导演Agent作为工作流第一个节点 |
| EventBus | 基础设施集成 | 所有状态变更通过EventBus发布 |

---

## 7. 详细实施计划

### 7.1 文件变更清单

#### 新增文件

| 文件 | 职责 | 行数估计 |
|------|------|---------|
| `src/deepnovel/scheduling/__init__.py` | 包初始化 | 20 |
| `src/deepnovel/scheduling/workflow_engine.py` | 工作流引擎 | 400 |
| `src/deepnovel/scheduling/task_scheduler.py` | 任务调度器 | 350 |
| `src/deepnovel/scheduling/checkpoint.py` | 断点管理器 | 150 |
| `src/deepnovel/scheduling/event_store.py` | 事件存储 | 120 |
| `src/deepnovel/scheduling/metrics.py` | 指标采集器 | 200 |
| `src/deepnovel/scheduling/persistence.py` | 任务持久化 | 100 |
| `frontend/src/views/WorkflowGraphView.vue` | DAG可视化 | 300 |
| `frontend/src/views/ExecutionTimelineView.vue` | 时间线 | 250 |
| `frontend/src/views/RealtimeMetricsView.vue` | 实时指标 | 200 |
| `frontend/src/composables/useWebSocket.ts` | WebSocket封装 | 80 |
| `frontend/src/services/websocket.ts` | WS服务 | 60 |

#### 修改文件

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/deepnovel/api/routes.py` | 新增WebSocket/SSE/可视化端点 | 增加7个端点 |
| `src/deepnovel/api/main.py` | 添加WebSocket支持 | 少量修改 |
| `src/deepnovel/core/performance_monitor.py` | 重定向到MetricsCollector | 向后兼容 |
| `src/deepnovel/core/event_bus.py` | 集成EventStore | 增强 |
| `frontend/src/router/index.ts` | 新增路由 | 3个新视图 |
| `frontend/src/views/TaskMonitorView.vue` | 增强（WebSocket+DAG入口） | 修改 |
| `frontend/package.json` | 新增d3依赖 | +d3 |

#### 删除文件

| 文件 | 说明 |
|------|------|
| `src/deepnovel/agents/coordinator.py` | 功能合并到TaskOrchestrator+TaskScheduler |
| `src/deepnovel/agents/task_manager.py` | 功能合并到TaskScheduler |
| `src/deepnovel/agents/workflow_orchestrator.py` | 冗余 |
| `src/deepnovel/agents/enhanced_workflow_orchestrator.py` | 冗余 |
| `src/deepnovel/messaging/rocketmq_producer.py` | 用EventBus替代 |
| `src/deepnovel/messaging/rocketmq_consumer.py` | 用EventBus替代 |

### 7.2 实施阶段

#### Phase 1: 核心引擎搭建（Day 1-4）

```
Day 1: TaskOrchestrator
- 实现WorkflowGraph/CompiledWorkflow/TaskOrchestrator
- 节点状态机
- 并行执行（信号量控制）
- 重试策略
- 单元测试

Day 2: TaskScheduler
- 优先级队列（最小堆）
- 调度主循环
- 并发控制
- 任务CRUD
- 单元测试

Day 3: Checkpoint + EventStore
- CheckpointManager（SQLite+文件）
- EventStore（时序存储）
- 持久化恢复逻辑
- 单元测试

Day 4: MetricsCollector + 集成
- MetricsCollector实现
- EventBus集成EventStore
- TaskOrchestrator集成CheckpointManager
- 端到端测试
```

#### Phase 2: 后端API扩展（Day 5-7）

```
Day 5: WebSocket + SSE
- FastAPI WebSocket端点
- 事件订阅管理
- SSE流实现
- 连接管理

Day 6: 可视化API
- /workflows/{id}/definition
- /workflows/{id}/state
- /workflows/{id}/timeline
- /metrics/timeseries
- Prometheus导出

Day 7: 集成测试
- API端到端测试
- WebSocket压力测试
- 并发任务测试
```

#### Phase 3: 前端可视化（Day 8-12）

```
Day 8: 基础设置
- 安装d3.js
- WebSocket composable
- API服务扩展

Day 9: WorkflowGraphView
- D3力导向图
- 节点着色（状态）
- 交互（点击/拖拽/缩放）
- WebSocket实时更新

Day 10: ExecutionTimelineView
- Gantt图实现
- 时间轴缩放
- 并行段高亮
- 节点详情弹窗

Day 11: RealtimeMetricsView
- ECharts集成
- 实时折线图
- 仪表盘组件
- 告警列表

Day 12: TaskMonitor增强
- WebSocket替代轮询
- DAG入口按钮
- 时间线跳转
- 整合测试
```

#### Phase 4: 系统集成（Day 13-15）

```
Day 13: Agent层对接
- BaseAgent.process绑定TaskOrchestrator
- DirectorAgent作为工作流入口
- 状态分区读写
- 集成测试

Day 14: 旧代码迁移
- Coordinator迁移到TaskOrchestrator
- TaskManager迁移到TaskScheduler
- 删除旧文件
- API兼容性验证

Day 15: 性能优化
- 数据库索引优化
- WebSocket广播优化
- Checkpoint压缩
- 内存使用优化
```

#### Phase 5: 测试与文档（Day 16-18）

```
Day 16: 压力测试
- 100并发任务测试
- WebSocket 1000连接测试
- 大数据量EventStore测试
- 内存泄漏检测

Day 17: 故障测试
- 节点失败重试
- 断点恢复
- 调度器崩溃恢复
- 网络断开重连

Day 18: 文档完善
- API文档更新
- 部署指南
- 监控配置
- 运维手册
```

### 7.3 关键里程碑

| 里程碑 | 日期 | 验收标准 |
|--------|------|---------|
| M1: 引擎可用 | Day 4 | TaskOrchestrator + TaskScheduler单机运行，10个节点DAG执行成功 |
| M2: API就绪 | Day 7 | 所有REST/WebSocket/SSE端点可用，通过Postman测试 |
| M3: 可视化可用 | Day 12 | 前端三个新视图可正常显示，WebSocket实时更新延迟<500ms |
| M4: 系统对接 | Day 15 | 与Step4 Agent层完整对接，端到端小说生成任务可执行 |
| M5: 生产就绪 | Day 18 | 压力测试通过，文档完整，可上线运行 |

---

## 8. 量化验收标准

### 8.1 功能验收

| 编号 | 功能 | 验收标准 |
|------|------|---------|
| F1 | DAG定义 | 支持10+节点的DAG定义，含条件分支和并行节点 |
| F2 | 工作流执行 | 完整执行一个小说生成工作流，所有节点状态正确流转 |
| F3 | 断点恢复 | 在任意节点失败后，从checkpoint恢复，不重复执行已完成节点 |
| F4 | 优先级调度 | 高优先级任务先于低优先级执行 |
| F5 | 并发控制 | 并发任务数不超过配置上限，超额任务排队等待 |
| F6 | 事件持久化 | 所有工作流事件写入EventStore，支持查询和回放 |
| F7 | DAG可视化 | 前端可渲染完整DAG，节点状态实时着色 |
| F8 | 执行时间线 | Gantt图正确展示各节点执行时段和并行关系 |
| F9 | 实时推送 | WebSocket推送延迟<500ms，前端无轮询 |
| F10 | 指标监控 | 可查看任务吞吐量、节点耗时、队列深度等指标 |
| F11 | 定时任务 | 支持Cron表达式定时触发工作流 |
| F12 | 告警系统 | 节点失败/超时自动告警，WebSocket推送告警事件 |

### 8.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 任务调度延迟 | < 100ms (从提交到开始执行) | 1000次提交取平均 |
| WebSocket推送延迟 | < 500ms (事件产生到前端接收) | 网络抓包测量 |
| DAG渲染时间 | < 2s (20节点DAG首次渲染) | 前端Performance API |
| 并发任务数 | >= 10 | 同时提交10个任务，全部正常运行 |
| 事件存储吞吐量 | >= 1000 events/sec | 批量写入测试 |
| 断点恢复时间 | < 5s | 从checkpoint恢复到继续执行 |

### 8.3 架构验收

| 检查项 | 标准 |
|--------|------|
| 无单点故障 | TaskScheduler崩溃后可恢复，运行中任务不丢失 |
| 状态一致性 | EventStore、Checkpoint、内存状态三者一致 |
| 向后兼容 | 原有REST API（/tasks等）行为不变 |
| 可观测性 | 任意工作流可查看完整执行历史和当前状态 |
| 可扩展性 | 新增工作流类型无需修改引擎代码 |

---

## 9. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| WebSocket连接大量断开 | 中 | 高 | 实现自动重连机制，降级到轮询 |
| EventStore数据库过大 | 中 | 中 | 实现自动归档和清理策略 |
| D3.js性能瓶颈（大DAG） | 低 | 中 | 超过50节点时启用分层渲染 |
| 断点恢复状态不一致 | 低 | 高 | 状态版本校验，不一致时重新执行 |
| 定时任务漂移 | 中 | 低 | 使用apscheduler或croniter库 |

---

## 10. 附录

### A. 前端路由规划

```typescript
// 新增路由
{
  path: 'workflows',
  children: [
    {
      path: 'graph/:workflowId',
      name: 'WorkflowGraph',
      component: () => import('@/views/WorkflowGraphView.vue'),
      meta: { title: '工作流图', icon: 'Share' }
    },
    {
      path: 'timeline/:workflowId',
      name: 'ExecutionTimeline',
      component: () => import('@/views/ExecutionTimelineView.vue'),
      meta: { title: '执行时间线', icon: 'Timer' }
    }
  ]
},
{
  path: 'metrics',
  name: 'RealtimeMetrics',
  component: () => import('@/views/RealtimeMetricsView.vue'),
  meta: { title: '实时监控', icon: 'DataLine' }
}
```

### B. 数据库Schema

```sql
-- checkpoints表（已包含在CheckpointManager中）
-- events表（已包含在EventStore中）

-- 新增：tasks表（持久化任务队列）
CREATE TABLE scheduled_tasks (
    task_id TEXT PRIMARY KEY,
    workflow_name TEXT NOT NULL,
    priority INTEGER DEFAULT 2,
    state TEXT DEFAULT 'pending',
    scheduled_time REAL,
    created_at REAL DEFAULT (unixepoch()),
    started_at REAL,
    completed_at REAL,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    timeout_seconds REAL DEFAULT 3600,
    user_id TEXT,
    error_message TEXT,
    metadata TEXT,
    workflow_instance_id TEXT
);

CREATE INDEX idx_task_state ON scheduled_tasks(state);
CREATE INDEX idx_task_user ON scheduled_tasks(user_id);
CREATE INDEX idx_task_scheduled ON scheduled_tasks(scheduled_time);
```

### C. 依赖清单

```
# Python新增依赖
aiosqlite>=0.19.0          # 异步SQLite
croniter>=2.0.0            # Cron表达式解析
prometheus-client>=0.17.0  # Prometheus指标导出（可选）

# 前端新增依赖
npm install d3@7           # DAG可视化
npm install echarts@5      # 指标图表
```

---

> **文档结束**
>
> 下一步：按Phase 1开始实施，优先搭建TaskOrchestrator和TaskScheduler核心框架。
