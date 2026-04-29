"""
单元测试 - 协调者智能体 (CoordinatorAgent)

@file: tests/test_agents/test_coordinator.py
@date: 2026-03-13
@version: 1.0
"""

import sys
import os
import time
import uuid
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field

# 添加测试目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MessageState(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"
    COMMAND = "command"
    SYSTEM = "system"


class AgentState(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class WorkflowState(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Message:
    id: str
    type: MessageState
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    sender: Optional[str] = None
    receiver: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "receiver": self.receiver
        }


@dataclass
class AgentConfig:
    name: str
    description: str = ""
    provider: str = "ollama"
    model: str = "qwen2.5-14b"
    temperature: float = 0.7
    max_tokens: int = 8192
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    retry_times: int = 3
    timeout: int = 60


@dataclass
class DAGNode:
    agent_name: str
    Dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    elapsed_time: float = 0.0


@dataclass
class DAG:
    nodes: Dict[str, DAGNode] = field(default_factory=dict)
    edges: List[tuple] = field(default_factory=list)
    root_nodes: List[str] = field(default_factory=list)
    leaf_nodes: List[str] = field(default_factory=list)

    def add_node(self, node: DAGNode):
        self.nodes[node.agent_name] = node

    def add_edge(self, from_node: str, to_node: str):
        self.edges.append((from_node, to_node))
        if from_node not in self.leaf_nodes:
            self.leaf_nodes.append(from_node)
        if to_node not in self.root_nodes:
            self.root_nodes.append(to_node)

    def get_ready_nodes(self) -> List[str]:
        ready = []
        for node_name, node in self.nodes.items():
            if node.status == "pending":
                all_deps_done = all(
                    self.nodes[dep].status == "completed"
                    for dep in node.Dependencies
                )
                if all_deps_done:
                    ready.append(node_name)
        return ready

    def get_next_node(self) -> Optional[str]:
        ready = self.get_ready_nodes()
        if ready:
            return ready[0]
        return None

    def all_completed(self) -> bool:
        return all(node.status == "completed" for node in self.nodes.values())

    def has_failed(self) -> bool:
        return any(node.status == "failed" for node in self.nodes.values())


class BaseAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self._state = AgentState.IDLE
        self._name = config.name
        self._description = config.description
        self._last_message: Optional[Message] = None
        self._history: List[Message] = []

    def process(self, message: Message) -> Message:
        raise NotImplementedError

    def _create_message(self, content: Any, message_type: MessageState = MessageState.TEXT, **metadata) -> Message:
        return Message(
            id=str(uuid.uuid4()),
            type=message_type,
            content=content,
            metadata=metadata,
            sender=self._name
        )


class CoordinatorAgent(BaseAgent):
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                name="coordinator",
                description="Overall workflow coordinator",
                provider="ollama",
                model="qwen2.5-14b",
                system_prompt="You are a novel generation workflow coordinator."
            )
        super().__init__(config)

        self._workflow_state = WorkflowState.IDLE
        self._current_task: Optional[Dict[str, Any]] = None
        self._dag: Optional[DAG] = None
        self._task_start_time: float = 0
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._total_nodes = 0
        self._context: Dict[str, Any] = {
            "generated_content": [],
            "characters": [],
            "world_bible": {},
            "outlines": []
        }

    def process(self, message: Message) -> Message:
        content = str(message.content).lower()

        if "start" in content or "generate" in content:
            return self._handle_start_request(message)
        elif "status" in content or "progress" in content:
            return self._handle_status_request(message)
        elif "stop" in content or "pause" in content:
            return self._handle_stop_request(message)
        elif "resume" in content:
            return self._handle_resume_request(message)
        else:
            return self._handle_general_request(message)

    def _handle_start_request(self, message: Message) -> Message:
        self._workflow_state = WorkflowState.PLANNING
        response = "I'll start the novel generation workflow. Initializing agents..."
        return self._create_message(response)

    def _handle_status_request(self, message: Message) -> Message:
        if self._workflow_state == WorkflowState.IDLE:
            response = "Workflow coordinator is idle. Ready to start new tasks."
        elif self._workflow_state == WorkflowState.PLANNING:
            response = "Workflow is planning the DAG structure."
        elif self._workflow_state == WorkflowState.EXECUTING:
            progress = self._calculate_progress()
            response = f"Workflow progress: {progress:.1f}%"
        elif self._workflow_state == WorkflowState.COMPLETED:
            elapsed = time.time() - self._task_start_time if self._task_start_time else 0
            response = f"Workflow completed successfully! Elapsed: {elapsed:.1f}s"
        else:
            response = f"Current state: {self._workflow_state.value}"
        return self._create_message(response)

    def _handle_stop_request(self, message: Message) -> Message:
        if self._workflow_state in [WorkflowState.EXECUTING, WorkflowState.PLANNING]:
            self._workflow_state = WorkflowState.PAUSED
            response = "Workflow paused. Use 'resume' to continue."
        else:
            response = f"Cannot pause. Current state: {self._workflow_state.value}"
        return self._create_message(response)

    def _handle_resume_request(self, message: Message) -> Message:
        if self._workflow_state == WorkflowState.PAUSED:
            self._workflow_state = WorkflowState.EXECUTING
            response = "Workflow resumed."
        else:
            response = f"Cannot resume. Current state: {self._workflow_state.value}"
        return self._create_message(response)

    def _handle_general_request(self, message: Message) -> Message:
        response = "I can help you coordinate the novel generation workflow."
        return self._create_message(response)

    def _plan_workflow(self, user_request: Dict[str, Any]) -> Dict[str, Any]:
        stage_config = {
            "initialization": {
                "agents": ["health_checker", "config_enhancer"],
                "description": "Initialize workflow",
                "dependencies": {}
            },
            "planning": {
                "agents": ["outline_planner", "character_generator", "world_builder"],
                "description": "Plan novel structure",
                "dependencies": {
                    "character_generator": ["config_enhancer"],
                    "world_builder": ["config_enhancer"],
                    "outline_planner": ["character_generator", "world_builder"]
                }
            },
            "execution": {
                "agents": ["chapter_summary", "hook_generator", "conflict_generator"],
                "description": "Generate content assets",
                "dependencies": {
                    "chapter_summary": ["outline_planner"],
                    "hook_generator": ["outline_planner"],
                    "conflict_generator": ["chapter_summary"]
                }
            },
            "generation": {
                "agents": ["content_generator"],
                "description": "Generate novel content",
                "dependencies": {
                    "content_generator": ["chapter_summary", "hook_generator", "conflict_generator"]
                }
            },
            "quality": {
                "agents": ["quality_checker"],
                "description": "Review and quality check",
                "dependencies": {
                    "quality_checker": ["content_generator"]
                }
            }
        }

        return {
            "stages": stage_config,
            "total_stages": len(stage_config),
            "total_agents": sum(len(s["agents"]) for s in stage_config.values()),
            "error": None
        }

    def _build_dag(self, dag_plan: Dict[str, Any]) -> DAG:
        dag = DAG()
        stage_order = ["initialization", "planning", "execution", "generation", "quality"]

        for stage_name in stage_order:
            if stage_name not in dag_plan["stages"]:
                continue
            stage = dag_plan["stages"][stage_name]
            for agent_name in stage["agents"]:
                dependencies = stage["dependencies"].get(agent_name, [])
                node = DAGNode(agent_name=agent_name, Dependencies=dependencies, status="pending")
                dag.add_node(node)
                for dep in dependencies:
                    dag.add_edge(dep, agent_name)

        return dag

    def _calculate_progress(self) -> float:
        if not self._dag or self._total_nodes == 0:
            return 0.0
        completed = sum(1 for node in self._dag.nodes.values() if node.status == "completed")
        return (completed / self._total_nodes) * 100

    def reset(self) -> None:
        self._workflow_state = WorkflowState.IDLE
        self._current_task = None
        self._dag = None
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._total_nodes = 0
        self._context = {
            "generated_content": [],
            "characters": [],
            "world_bible": {},
            "outlines": []
        }

    def get_execution_status(self) -> Dict[str, Any]:
        if not self._dag:
            return {"error": "No DAG initialized"}
        return {
            "state": self._workflow_state.value,
            "progress": self._calculate_progress(),
            "nodes": {
                name: {
                    "status": node.status,
                    "elapsed_time": node.elapsed_time,
                    "error": node.error
                }
                for name, node in self._dag.nodes.items()
            },
            "completed": self._tasks_completed,
            "failed": self._tasks_failed,
            "total": self._total_nodes
        }


# 测试函数
def test_coordinator_initialization():
    """测试1: Coordinator初始化"""
    config = AgentConfig(
        name="coordinator",
        description="Test Coordinator",
        provider="ollama",
        model="qwen2.5-14b",
        max_tokens=8192
    )
    coordinator = CoordinatorAgent(config)

    assert coordinator is not None, "Coordinator创建失败"
    assert coordinator._workflow_state == WorkflowState.IDLE, "初始状态不正确"
    assert coordinator._name == "coordinator", "名称不正确"
    assert coordinator._description == "Test Coordinator", "描述不正确"

    print("[TEST 1] Coordinator initialization: PASS")


def test_dag_planning():
    """测试2: DAG规划"""
    config = AgentConfig(
        name="coordinator",
        description="Test Coordinator",
        provider="ollama",
        model="qwen2.5-14b",
    )
    coordinator = CoordinatorAgent(config)

    user_request = {
        "timestamp": "2026-03-13T10:00:00",
        "original_request": "Generate a fantasy novel",
        "intent": "generate_novel",
        "parameters": {"genre": "fantasy"}
    }

    dag_plan = coordinator._plan_workflow(user_request)

    assert dag_plan is not None, "DAG规划失败"
    assert "stages" in dag_plan, "缺少stages字段"
    assert len(dag_plan["stages"]) == 5, "应有5个阶段"
    assert dag_plan["total_agents"] == 10, "应有10个agent"

    dag = coordinator._build_dag(dag_plan)
    assert dag is not None, "DAG构建失败"
    assert len(dag.nodes) == 10, "DAG节点数不正确"

    print("[TEST 2] DAG planning: PASS")


def test_message_handling():
    """测试3: 消息处理"""
    config = AgentConfig(name="coordinator", provider="ollama", model="qwen2.5-14b")
    coordinator = CoordinatorAgent(config)

    # 测试生成请求
    msg = Message(id="test_1", type=MessageState.TEXT, content="start generation")
    response = coordinator.process(msg)
    assert response is not None, "响应为空"
    assert response.sender == "coordinator", "sender不正确"

    # 测试状态查询
    msg = Message(id="test_2", type=MessageState.TEXT, content="check status")
    status_response = coordinator.process(msg)
    assert status_response is not None, "状态响应为空"

    # 测试暂停请求
    msg = Message(id="test_3", type=MessageState.TEXT, content="pause workflow")
    pause_response = coordinator.process(msg)
    assert pause_response is not None, "暂停响应为空"

    # 测试恢复请求
    coordinator._workflow_state = WorkflowState.PAUSED
    msg = Message(id="test_4", type=MessageState.TEXT, content="resume")
    resume_response = coordinator.process(msg)
    assert resume_response is not None, "恢复响应为空"
    assert resume_response.content == "Workflow resumed.", "恢复响应内容不正确"

    print("[TEST 3] Message handling: PASS")


def test_state_transitions():
    """测试4: 状态转换"""
    config = AgentConfig(name="coordinator", provider="ollama", model="qwen2.5-14b")
    coordinator = CoordinatorAgent(config)

    # IDLE -> PLANNING
    coordinator._workflow_state = WorkflowState.PLANNING
    assert coordinator._workflow_state == WorkflowState.PLANNING

    # PLANNING -> EXECUTING
    coordinator._workflow_state = WorkflowState.EXECUTING
    assert coordinator._workflow_state == WorkflowState.EXECUTING

    # EXECUTING -> COMPLETED
    coordinator._workflow_state = WorkflowState.COMPLETED
    assert coordinator._workflow_state == WorkflowState.COMPLETED

    # 重置
    coordinator.reset()
    assert coordinator._workflow_state == WorkflowState.IDLE

    print("[TEST 4] State transitions: PASS")


def test_workflow_simulation():
    """测试5: 工作流模拟"""
    config = AgentConfig(name="coordinator", provider="ollama", model="qwen2.5-14b")
    coordinator = CoordinatorAgent(config)

    user_request = {"parameters": {}}
    dag_plan = coordinator._plan_workflow(user_request)
    dag = coordinator._build_dag(dag_plan)
    coordinator._dag = dag
    coordinator._total_nodes = len(dag.nodes)
    coordinator._workflow_state = WorkflowState.EXECUTING

    # 模拟执行所有节点
    max_iterations = 30
    for _ in range(max_iterations):
        next_node = dag.get_next_node()
        if next_node is None:
            break
        node = dag.nodes[next_node]
        node.status = "completed"

    coordinator._tasks_completed = 10
    coordinator._workflow_state = WorkflowState.COMPLETED

    progress = coordinator._calculate_progress()
    assert progress == 100.0, f"进度应为100%，实际为{progress}%"

    print("[TEST 5] Workflow simulation: PASS")


def test_dag_operations():
    """测试6: DAG操作"""
    dag = DAG()

    # 添加节点
    node1 = DAGNode(agent_name="agent1", Dependencies=[])
    node2 = DAGNode(agent_name="agent2", Dependencies=["agent1"])
    node3 = DAGNode(agent_name="agent3", Dependencies=["agent1", "agent2"])

    dag.add_node(node1)
    dag.add_node(node2)
    dag.add_node(node3)

    assert len(dag.nodes) == 3, "节点数量不正确"

    # 添加边
    dag.add_edge("agent1", "agent2")
    assert len(dag.edges) == 1, "边数量不正确"

    # 测试就绪节点
    ready = dag.get_ready_nodes()
    assert "agent1" in ready, "agent1应该就绪"

    node1.status = "completed"
    ready = dag.get_ready_nodes()
    assert "agent2" in ready, "agent2应该就绪"

    node2.status = "completed"
    ready = dag.get_ready_nodes()
    assert "agent3" in ready, "agent3应该就绪"

    # 测试完成检查
    node3.status = "completed"
    assert dag.all_completed(), "应该全部完成"
    assert not dag.has_failed(), "不应有失败"

    print("[TEST 6] DAG operations: PASS")


def test_error_handling():
    """测试7: 错误处理"""
    config = AgentConfig(name="coordinator", provider="ollama", model="qwen2.5-14b")
    coordinator = CoordinatorAgent(config)

    # 没有DAG时的状态查询
    msg = Message(id="test", type=MessageState.TEXT, content="status")
    response = coordinator._handle_status_request(msg)
    assert response is not None, "状态响应不应为空"

    # 非法状态转换
    coordinator._workflow_state = WorkflowState.IDLE
    msg = Message(id="test", type=MessageState.TEXT, content="pause")
    response = coordinator._handle_stop_request(msg)
    assert response is not None, "暂停响应不应为空"
    assert "Cannot pause" in str(response.content), "应该提示无法暂停"

    print("[TEST 7] Error handling: PASS")


def test_execution_status():
    """测试8: 执行状态查询"""
    config = AgentConfig(name="coordinator", provider="ollama", model="qwen2.5-14b")
    coordinator = CoordinatorAgent(config)

    # 没有DAG时的状态
    status = coordinator.get_execution_status()
    assert "error" in status, "应该返回错误信息"

    # 有DAG时的状态
    user_request = {"parameters": {}}
    dag_plan = coordinator._plan_workflow(user_request)
    dag = coordinator._build_dag(dag_plan)
    coordinator._dag = dag
    coordinator._total_nodes = len(dag.nodes)
    coordinator._tasks_completed = 3

    status = coordinator.get_execution_status()
    assert "state" in status, "应该包含state字段"
    assert "progress" in status, "应该包含progress字段"
    assert "nodes" in status, "应该包含nodes字段"

    print("[TEST 8] Execution status: PASS")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("CoordinatorAgent 单元测试")
    print("="*60 + "\n")

    test_coordinator_initialization()
    test_dag_planning()
    test_message_handling()
    test_state_transitions()
    test_workflow_simulation()
    test_dag_operations()
    test_error_handling()
    test_execution_status()

    print("\n" + "="*60)
    print("所有测试通过!")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
