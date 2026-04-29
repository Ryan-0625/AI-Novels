# Step 11: API网关层重构 - Agent编排能力的HTTP暴露层

> 版本: 1.0
> 日期: 2026-04-28
> 依赖: Step1-10（特别是Step4 Agent层、Step5 任务调度层、Step7 配置补全层、Step10 配置层）
> 目标: 将Agent编排能力通过统一HTTP API暴露，支持异步任务提交、状态轮询/SSE、配置热加载

---

## 1. 设计哲学

### 1.1 核心转变

```
从：路由直接操作底层Agent（紧耦合）    → 到：路由提交任务到TaskOrchestrator（松耦合）
从：同步阻塞API（长连接等待生成）      → 到：异步API + 状态轮询/SSE（非阻塞）
从：硬编码配置读取（settings.get()）    → 到：统一ConfigHub获取（类型安全）
从：单体routes.py（350+行混杂路由）    → 到：按领域拆分API模块（单一职责）
从：内存任务状态（丢失即无）            → 到：持久化任务队列（数据库+事件日志）
从：无统一错误格式                     → 到：标准化错误响应（RFC 7807风格）
```

### 1.2 设计原则

1. **API即门面**: API层是Agent编排能力的唯一HTTP暴露入口，禁止绕过API直接操作Agent
2. **异步即默认**: 所有耗时操作（小说生成、配置补全）默认异步，返回任务ID
3. **配置即中枢**: 所有配置通过ConfigHub获取，API层不直接读取文件或环境变量
4. **事件即推送**: 任务状态变更通过SSE/WebSocket推送，减少轮询
5. **版本即兼容**: API路径版本化（/api/v1/...），支持多版本共存
6. **可观测即内置**: 每个请求自动记录trace_id、耗时、状态码，接入MetricsCollector

### 1.3 行业前沿参考

| 来源 | 核心借鉴 | 适用场景 |
|------|---------|---------|
| **FastAPI Best Practices** (2024) | 依赖注入、Pydantic模型、自动文档 | Python API开发 |
| **Temporal Web UI** (2024) | 工作流可视化 + API分离 | 任务编排前端 |
| **Prefect REST API** (2024) | 任务CRUD + 状态流 + 日志流 | 工作流API设计 |
| **LangServe** (2024) | Agent即服务、流式输出、可观测 | AI服务暴露 |
| **OpenAPI Generator** | 代码生成、类型安全客户端 | 前后端契约 |
| **API Gateway Pattern** | 统一入口、认证、限流、路由 | 微服务网关 |

---

## 2. 现状诊断

### 2.1 当前API层组件清单

| 组件 | 文件 | 问题 | 严重程度 |
|------|------|------|---------|
| `routes.py` | `api/routes.py` (352行) | 所有路由混杂在一个文件；直接调用`CoordinatorAgent`；无任务调度概念 | **严重** |
| `controllers.py` | `api/controllers.py` (781行) | `TaskController`直接实例化`CoordinatorAgent`；配置硬编码；内存存储任务 | **严重** |
| `middleware.py` | `api/middleware.py` (516行) | 基础中间件完整但**无ConfigHub集成**；`settings.get_database()`直接读旧配置 | **中** |
| `main.py` | `api/main.py` (177行) | 启动时加载旧`ConfigManager`；初始化`CoordinatorAgent`；无`ConfigHub` | **中** |
| 请求/响应模型 | `routes.py`内联定义 | 模型与路由耦合；无复用；部分字段类型不安全 | **中** |

### 2.2 核心问题总结

```
当前状态：API层是"直接操作层"而非"编排门面"

1. 路由直接调用Agent        → TaskController._execute_task()直接new CoordinatorAgent()
2. 同步阻塞生成             → 后台任务无状态持久化，重启即丢失
3. 旧配置系统依赖           → from src.deepnovel.config.manager import ConfigManager, settings
4. 无任务调度概念           → 无TaskOrchestrator/TaskScheduler集成
5. 无配置管理API            → /config/update直接操作内存字典
6. 无Agent管理API           → /agents返回硬编码列表
7. 健康检查简单             → 无依赖服务状态（LLM/DB/VectorStore）
8. 无SSE/WebSocket          → 前端只能轮询获取状态
```

---

## 3. 架构总览

### 3.1 API网关六层架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 6: 客户端层 (Clients)                                          │
│  • Web Frontend (Vue3)    - 小说生成界面、任务监控面板               │
│  • CLI Client             - 命令行工具                               │
│  • Third-party Apps       - 第三方集成                               │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 5: 协议适配层 (Protocol Adapters)                              │
│  • REST API (/api/v1/*)   - 标准CRUD                                 │
│  • SSE Stream (/events)   - 服务器推送事件                           │
│  • WebSocket (/ws/*)      - 双向实时通信                             │
│  • OpenAPI Docs (/docs)   - 自动生成的交互式文档                     │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 4: API领域层 (Domain APIs)                                     │
│  • NovelGenerationAPI     - 小说生成（提交/查询/结果）               │
│  • AgentManagementAPI     - Agent管理（列表/配置/状态）              │
│  • TaskManagementAPI      - 任务管理（工作流/暂停/恢复/取消）        │
│  • ConfigAPI              - 配置管理（查看/热加载/验证）             │
│  • HealthCheckAPI         - 健康检查（含依赖服务状态）               │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: 编排服务层 (Orchestration Services)                         │
│  • NovelGenerationService - 小说生成业务服务                         │
│  • AgentRegistryService   - Agent注册与发现服务                      │
│  • TaskQueryService       - 任务查询与状态聚合服务                   │
│  • ConfigQueryService     - 配置查询与变更服务                       │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: 核心基础设施层 (Core Infrastructure)                        │
│  • DirectorAgent          - 导演Agent（Step4）                       │
│  • TaskOrchestrator       - 任务编排引擎（Step5）                    │
│  • TaskScheduler          - 任务调度器（Step5）                      │
│  • ConfigHub              - 配置中枢（Step10）                       │
│  • EventBus               - 事件总线                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 1: 数据持久层 (Persistence)                                    │
│  • SQLite                 - 任务/工作流/事件存储                     │
│  • Qdrant                 - 向量语义检索                             │
│  • File System            - 小说输出文件                             │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 请求数据流

```
┌──────────┐     POST /api/v1/novels/generate      ┌──────────────┐
│  客户端   │ ────────────────────────────────────→ │              │
│ (Vue3)   │                                       │  NovelGenerationAPI
└──────────┘                                       │  (FastAPI Router)
     │                                             └──────┬───────┘
     │                                                    │
     │  202 Accepted {task_id: "task_xxx"}                │ 提交到
     │◄───────────────────────────────────────────────────┤ TaskScheduler
     │                                                    │
     │  GET /api/v1/tasks/task_xxx                        │
     │ ────────────────────────────────────────────────→  │
     │                                                    │
     │  200 OK {status: "running", progress: 45%}         │
     │◄───────────────────────────────────────────────────┤
     │                                                    │
     │  SSE /api/v1/tasks/task_xxx/stream                 │
     │ ────────────────────────────────────────────────→  │
     │  data: {"type": "node_completed", "node": "scene_writer"}
     │◄───────────────────────────────────────────────────┤ EventBus → SSE
     │  data: {"type": "task_completed", "result": {...}}
     │◄───────────────────────────────────────────────────┤
```

---

## 4. 核心组件设计

### 4.1 APIGateway - FastAPI应用工厂

**职责**: 统一FastAPI应用创建，集成ConfigHub初始化、中间件栈、路由注册

```python
# src/deepnovel/api/gateway.py

from typing import Optional, List, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from src.deepnovel.config import ConfigHub
from src.deepnovel.core.event_bus import EventBus
from src.deepnovel.utils import get_logger

from .middleware import (
    RequestIDMiddleware,
    TimingMiddleware,
    LoggingMiddleware,
    ErrorHandlingMiddleware,
    ConfigAwareMiddleware,  # 新增：ConfigHub集成
)
from .routes import (
    novel_router,
    agent_router,
    task_router,
    config_router,
    health_router,
)

logger = get_logger()


class APIGateway:
    """
    API网关 - FastAPI应用工厂

n    职责：
    1. 统一创建FastAPI应用实例
    2. 集成ConfigHub初始化
    3. 注册中间件栈
    4. 注册领域路由
    5. 管理生命周期事件

    用法：
        gateway = APIGateway()
        app = gateway.create_app()
        uvicorn.run(app, host="0.0.0.0", port=8000)
    """

    def __init__(self):
        self._config_hub: Optional[ConfigHub] = None
        self._event_bus: Optional[EventBus] = None
        self._app: Optional[FastAPI] = None

    def create_app(self) -> FastAPI:
        """创建并配置FastAPI应用"""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """应用生命周期管理"""
            await self._startup(app)
            yield
            await self._shutdown(app)

        self._app = FastAPI(
            title="AI-Novels API",
            description="AI小说生成系统 - Agent编排HTTP暴露层",
            version="2.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
            lifespan=lifespan,
        )

        # 注册中间件（按执行顺序）
        self._register_middlewares()

        # 注册路由
        self._register_routers()

        # 注册异常处理器
        self._register_exception_handlers()

        return self._app

    async def _startup(self, app: FastAPI):
        """应用启动初始化"""
        logger.info("API Gateway starting...")

        # 1. 初始化ConfigHub（最先初始化，其他组件依赖配置）
        self._config_hub = ConfigHub()
        config_ok = self._config_hub.initialize(
            config_dir="config",
            profile=None,  # 自动检测
            env_file="config/.env"
        )
        if not config_ok:
            logger.error("ConfigHub initialization failed!")
            # 不阻断启动，使用默认配置运行

        app.state.config_hub = self._config_hub
        logger.info("ConfigHub initialized")

        # 2. 初始化EventBus
        self._event_bus = EventBus()
        app.state.event_bus = self._event_bus
        logger.info("EventBus initialized")

        # 3. 初始化TaskScheduler（依赖ConfigHub + EventBus）
        from src.deepnovel.scheduling import TaskScheduler, TaskOrchestrator

        task_orchestrator = TaskOrchestrator(
            max_concurrent_nodes=self._config_hub.config.workflow.max_concurrent_tasks,
            event_bus=self._event_bus,
        )

        task_scheduler = TaskScheduler(
            task_orchestrator=task_orchestrator,
            max_concurrent_tasks=self._config_hub.config.workflow.max_concurrent_tasks,
            max_queue_size=100,
            event_bus=self._event_bus,
        )
        await task_scheduler.start()

        app.state.task_scheduler = task_scheduler
        app.state.task_orchestrator = task_orchestrator
        logger.info("TaskScheduler started")

        # 4. 初始化AgentRegistry（加载所有可用Agent）
        from src.deepnovel.agents import AgentRegistry
        agent_registry = AgentRegistry()
        app.state.agent_registry = agent_registry
        logger.info("AgentRegistry initialized")

        # 5. 注册工作流模板
        from src.deepnovel.scheduling import WorkflowGraph
        from src.deepnovel.agents.workflows import NovelGenerationWorkflow

        workflow = NovelGenerationWorkflow()
        compiled = workflow.compile()
        task_orchestrator.register_workflow(compiled)
        logger.info("Workflow templates registered")

        logger.info("API Gateway started successfully")

    async def _shutdown(self, app: FastAPI):
        """应用关闭清理"""
        logger.info("API Gateway shutting down...")

        if hasattr(app.state, "task_scheduler"):
            await app.state.task_scheduler.shutdown()
            logger.info("TaskScheduler shut down")

        logger.info("API Gateway shutdown complete")

    def _register_middlewares(self):
        """注册中间件栈"""
        app = self._app

        # CORS（最外层）
        config = self._config_hub.config if self._config_hub and self._config_hub.is_initialized else None
        cors_origins = config.api.cors_origins if config else ["*"]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 错误处理（捕获所有未处理异常）
        app.add_middleware(ErrorHandlingMiddleware)

        # 请求ID追踪
        app.add_middleware(RequestIDMiddleware)

        # 请求日志
        app.add_middleware(LoggingMiddleware)

        # 性能计时
        app.add_middleware(TimingMiddleware)

        # ConfigHub感知中间件（将配置注入请求状态）
        app.add_middleware(ConfigAwareMiddleware)

    def _register_routers(self):
        """注册领域路由"""
        app = self._app

        # 小说生成API
        app.include_router(novel_router, prefix="/api/v1/novels", tags=["Novel Generation"])

        # Agent管理API
        app.include_router(agent_router, prefix="/api/v1/agents", tags=["Agent Management"])

        # 任务管理API
        app.include_router(task_router, prefix="/api/v1/tasks", tags=["Task Management"])

        # 配置管理API
        app.include_router(config_router, prefix="/api/v1/config", tags=["Configuration"])

        # 健康检查API
        app.include_router(health_router, prefix="/api/v1/health", tags=["Health Check"])

    def _register_exception_handlers(self):
        """注册全局异常处理器"""
        app = self._app

        @app.exception_handler(ValueError)
        async def value_error_handler(request: Request, exc: ValueError):
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": str(exc),
                        "request_id": getattr(request.state, "request_id", None)
                    }
                }
            )

        @app.exception_handler(KeyError)
        async def key_error_handler(request: Request, exc: KeyError):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Resource not found: {str(exc)}",
                        "request_id": getattr(request.state, "request_id", None)
                    }
                }
            )
```

### 4.2 NovelGenerationAPI - 小说生成路由

**职责**: 小说生成相关接口（提交任务/查询状态/获取结果）

```python
# src/deepnovel/api/routes/novel.py

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncio
import json

from src.deepnovel.config import ConfigHub
from src.deepnovel.config.models.novel import NovelConfig
from src.deepnovel.scheduling import TaskScheduler, TaskPriority
from src.deepnovel.agents import AgentRegistry

router = APIRouter()


# ============================================================================
# 请求/响应模型
# ============================================================================

class NovelGenerateRequest(BaseModel):
    """小说生成请求"""
    title: str = Field(..., min_length=1, max_length=100, description="小说标题")
    genre: str = Field(..., description="小说类型: xianxia/wuxia/fantasy/sci-fi/...")
    description: Optional[str] = Field(None, description="小说描述/简介")
    chapters: int = Field(16, ge=1, le=1000, description="目标章节数")
    word_count_per_chapter: int = Field(3000, ge=500, le=50000, description="每章目标字数")
    style: Optional[str] = Field(None, description="写作风格")
    tone: Optional[str] = Field(None, description="基调")
    pov: Optional[str] = Field(None, description="视角: first_person/third_person_limited/...")
    target_audience: Optional[str] = Field(None, description="目标受众")
    # Step7: NovelConfig支持
    preset_names: Optional[List[str]] = Field(None, description="配置预设名称列表")
    enable_llm_completion: bool = Field(True, description="是否启用LLM智能补全配置")
    # 用户自定义配置覆盖
    custom_config: Optional[Dict[str, Any]] = Field(None, description="自定义配置字段")


class NovelGenerateResponse(BaseModel):
    """小说生成响应（异步提交）"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field("accepted", description="任务状态: accepted")
    message: str = Field(..., description="状态说明")
    estimated_duration: Optional[int] = Field(None, description="预计耗时（秒）")


class NovelStatusResponse(BaseModel):
    """小说生成状态响应"""
    task_id: str
    status: str = Field(..., description="pending/running/completed/failed/cancelled")
    progress: float = Field(..., ge=0, le=100, description="进度百分比")
    current_stage: Optional[str] = Field(None, description="当前执行阶段")
    current_node: Optional[str] = Field(None, description="当前执行节点")
    workflow_name: str = Field("novel_generation", description="工作流名称")
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class NovelResultResponse(BaseModel):
    """小说生成结果响应"""
    task_id: str
    novel_id: Optional[str] = None
    title: str
    genre: str
    total_chapters: int
    total_word_count: int
    chapters: List[Dict[str, Any]] = Field(default_factory=list)
    download_url: Optional[str] = None


# ============================================================================
# 依赖注入
# ============================================================================

def get_task_scheduler(request: Request) -> TaskScheduler:
    """获取TaskScheduler实例（依赖注入）"""
    scheduler = getattr(request.app.state, "task_scheduler", None)
    if not scheduler:
        raise HTTPException(status_code=503, detail="Task scheduler not initialized")
    return scheduler


def get_config_hub(request: Request) -> ConfigHub:
    """获取ConfigHub实例（依赖注入）"""
    hub = getattr(request.app.state, "config_hub", None)
    if not hub or not hub.is_initialized:
        raise HTTPException(status_code=503, detail="ConfigHub not initialized")
    return hub


# ============================================================================
# API端点
# ============================================================================

@router.post("/generate", response_model=NovelGenerateResponse, summary="提交小说生成任务")
async def generate_novel(
    request: NovelGenerateRequest,
    background_tasks: BackgroundTasks,
    scheduler: TaskScheduler = Depends(get_task_scheduler),
    config_hub: ConfigHub = Depends(get_config_hub),
):
    """
    提交异步小说生成任务

    流程：
    1. 构建NovelConfig（使用Step7的ConfigComposer）
    2. 提交到TaskScheduler（Step5）
    3. 返回task_id供后续查询

    - **title**: 小说标题
    - **genre**: 小说类型
    - **preset_names**: 预设名称（如["xianxia", "literary"]）
    - **enable_llm_completion**: 是否让LLM自动补全缺失配置
    """
    # Step7: 使用ConfigComposer构建NovelConfig
    from src.deepnovel.config.composer import ConfigComposer
    from src.deepnovel.config.presets import PresetManager

    preset_manager = PresetManager()
    composer = ConfigComposer(preset_manager=preset_manager)

    # 组合配置
    user_input = request.model_dump(exclude={"preset_names", "enable_llm_completion"})
    novel_config = await composer.compose(
        user_input=user_input,
        preset_names=request.preset_names or [],
        enable_llm_completion=request.enable_llm_completion,
        context=request.description or ""
    )

    # 构建工作流初始状态
    initial_state = {
        "novel_config": novel_config.model_dump(),
        "user_request": request.model_dump(),
        "generation_stage": "initialized",
    }

    # 提交到TaskScheduler（Step5）
    task_id = await scheduler.submit(
        workflow_name="novel_generation",
        initial_state=initial_state,
        priority=TaskPriority.NORMAL,
        user_id="anonymous",  # TODO: 从认证信息获取
    )

    # 估算耗时（基于章节数和字数）
    estimated = estimate_duration(request.chapters, request.word_count_per_chapter)

    return NovelGenerateResponse(
        task_id=task_id,
        status="accepted",
        message=f"Novel generation task submitted. Task ID: {task_id}",
        estimated_duration=estimated
    )


@router.get("/status/{task_id}", response_model=NovelStatusResponse, summary="查询小说生成状态")
async def get_novel_status(
    task_id: str,
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """
    获取小说生成任务的当前状态

    - **task_id**: 任务ID（从generate接口返回）
    """
    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # 获取工作流实例状态（如果正在运行）
    workflow_state = None
    if task.workflow_instance_id:
        orchestrator = getattr(scheduler, "_workflow_engine", None)
        if orchestrator:
            workflow_state = orchestrator.get_instance(task.workflow_instance_id)

    return NovelStatusResponse(
        task_id=task_id,
        status=task.state.value if hasattr(task.state, "value") else str(task.state),
        progress=workflow_state.progress if workflow_state else 0.0,
        current_stage=task.metadata.get("current_stage") if hasattr(task, "metadata") else None,
        current_node=workflow_state.current_node if workflow_state else None,
        workflow_name=task.workflow_name,
        started_at=isoformat(task.started_at) if task.started_at else None,
        completed_at=isoformat(task.completed_at) if task.completed_at else None,
        error=task.error_message,
    )


@router.get("/result/{task_id}", response_model=NovelResultResponse, summary="获取小说生成结果")
async def get_novel_result(
    task_id: str,
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """
    获取已完成的小说生成结果

    - **task_id**: 任务ID
    """
    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.state.value != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed yet. Current status: {task.state.value}"
        )

    # 从持久化存储加载结果
    # TODO: 从数据库/文件系统加载小说内容
    return NovelResultResponse(
        task_id=task_id,
        title="Generated Novel",  # 从结果中提取
        genre="fantasy",
        total_chapters=16,
        total_word_count=48000,
        chapters=[]
    )


@router.get("/stream/{task_id}", summary="SSE流式获取任务状态")
async def stream_novel_status(
    task_id: str,
    request: Request,
):
    """
    通过SSE实时推送任务状态变更

    事件类型：
    - `task_started`: 任务开始
    - `node_started`: 节点开始执行
    - `node_completed`: 节点执行完成
    - `task_completed`: 任务完成
    - `task_failed`: 任务失败

    - **task_id**: 任务ID
    """
    event_bus = getattr(request.app.state, "event_bus", None)
    if not event_bus:
        raise HTTPException(status_code=503, detail="EventBus not initialized")

    async def event_generator():
        queue = asyncio.Queue()

        async def handler(event):
            if event.payload.get("task_id") == task_id or event.payload.get("workflow_id") == task_id:
                await queue.put(event)

        # 订阅事件
        unsubscribe = event_bus.subscribe(f"task.*.{task_id}", handler)
        unsubscribe_all = event_bus.subscribe(f"workflow.*", handler)

        try:
            # 发送初始心跳
            yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id})}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    data = {
                        "type": event.type,
                        "timestamp": event.timestamp,
                        "payload": event.payload,
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                    # 任务结束则关闭流
                    if event.type in ("task_completed", "task_failed", "task_cancelled"):
                        break

                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        finally:
            unsubscribe()
            unsubscribe_all()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ============================================================================
# 辅助函数
# ============================================================================

def estimate_duration(chapters: int, word_count: int) -> int:
    """估算生成耗时（秒）"""
    # 假设：每1000字约需30秒（含LLM调用+后处理）
    words_per_second = 1000 / 30
    total_words = chapters * word_count
    return int(total_words / words_per_second)


def isoformat(timestamp: float) -> str:
    """时间戳转ISO格式"""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).isoformat()
```

### 4.3 AgentManagementAPI - Agent管理路由

**职责**: Agent管理接口（列出Agent/配置Agent/查看Agent状态）

```python
# src/deepnovel/api/routes/agent.py

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.deepnovel.agents import AgentRegistry
from src.deepnovel.config import ConfigHub

router = APIRouter()


# ============================================================================
# 请求/响应模型
# ============================================================================

class AgentInfoResponse(BaseModel):
    """Agent信息响应"""
    name: str = Field(..., description="Agent标识名")
    description: str = Field(..., description="Agent描述")
    layer: str = Field(..., description="所属层级: orchestration/simulation/narrative/quality")
    status: str = Field(..., description="状态: active/inactive/error")
    enabled: bool = Field(True, description="是否启用")
    llm_config: Optional[Dict[str, Any]] = None
    tools: List[str] = Field(default_factory=list, description="可用工具列表")
    metrics: Optional[Dict[str, Any]] = None


class AgentConfigUpdateRequest(BaseModel):
    """Agent配置更新请求"""
    enabled: Optional[bool] = None
    llm_override: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    max_history: Optional[int] = None
    timeout: Optional[float] = None
    custom_params: Optional[Dict[str, Any]] = None


class AgentConfigUpdateResponse(BaseModel):
    """Agent配置更新响应"""
    agent_name: str
    updated_fields: List[str]
    message: str


class AgentMetricsResponse(BaseModel):
    """Agent指标响应"""
    agent_name: str
    total_invocations: int
    average_duration_ms: float
    success_rate: float
    last_invoked_at: Optional[str] = None
    error_count: int


# ============================================================================
# 依赖注入
# ============================================================================

def get_agent_registry(request: Request) -> AgentRegistry:
    """获取AgentRegistry实例"""
    registry = getattr(request.app.state, "agent_registry", None)
    if not registry:
        raise HTTPException(status_code=503, detail="Agent registry not initialized")
    return registry


def get_config_hub(request: Request) -> ConfigHub:
    """获取ConfigHub实例"""
    hub = getattr(request.app.state, "config_hub", None)
    if not hub or not hub.is_initialized:
        raise HTTPException(status_code=503, detail="ConfigHub not initialized")
    return hub


# ============================================================================
# API端点
# ============================================================================

@router.get("", response_model=List[AgentInfoResponse], summary="列出所有Agent")
async def list_agents(
    layer: Optional[str] = None,
    status: Optional[str] = None,
    registry: AgentRegistry = Depends(get_agent_registry),
    config_hub: ConfigHub = Depends(get_config_hub),
):
    """
    获取系统中所有可用的Agent列表

    - **layer**: 按层级过滤 (orchestration/simulation/narrative/quality)
    - **status**: 按状态过滤 (active/inactive/error)
    """
    agents = registry.list_agents()

    # 从ConfigHub获取Agent配置
    config = config_hub.config

    result = []
    for agent_name, agent_info in agents.items():
        agent_config = config.get_agent(agent_name)

        if layer and agent_info.get("layer") != layer:
            continue
        if status and agent_info.get("status") != status:
            continue

        result.append(AgentInfoResponse(
            name=agent_name,
            description=agent_info.get("description", ""),
            layer=agent_info.get("layer", "unknown"),
            status=agent_info.get("status", "unknown"),
            enabled=agent_config.enabled if agent_config else True,
            llm_config=agent_config.llm_override.model_dump() if agent_config and agent_config.llm_override else None,
            tools=agent_config.tools if agent_config else [],
            metrics=agent_info.get("metrics"),
        ))

    return result


@router.get("/{agent_name}", response_model=AgentInfoResponse, summary="获取Agent详情")
async def get_agent_detail(
    agent_name: str,
    registry: AgentRegistry = Depends(get_agent_registry),
    config_hub: ConfigHub = Depends(get_config_hub),
):
    """
    获取指定Agent的详细信息

    - **agent_name**: Agent名称
    """
    agent_info = registry.get_agent(agent_name)
    if not agent_info:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    agent_config = config_hub.config.get_agent(agent_name)

    return AgentInfoResponse(
        name=agent_name,
        description=agent_info.get("description", ""),
        layer=agent_info.get("layer", "unknown"),
        status=agent_info.get("status", "unknown"),
        enabled=agent_config.enabled if agent_config else True,
        llm_config=agent_config.llm_override.model_dump() if agent_config and agent_config.llm_override else None,
        tools=agent_config.tools if agent_config else [],
        metrics=agent_info.get("metrics"),
    )


@router.patch("/{agent_name}/config", response_model=AgentConfigUpdateResponse, summary="更新Agent配置")
async def update_agent_config(
    agent_name: str,
    request: AgentConfigUpdateRequest,
    config_hub: ConfigHub = Depends(get_config_hub),
):
    """
    更新指定Agent的配置（运行时覆盖）

    注意：此更新仅影响当前运行实例，持久化需修改配置文件。

    - **agent_name**: Agent名称
    - **enabled**: 是否启用
    - **llm_override**: LLM配置覆盖
    - **tools**: 可用工具列表
    """
    agent_config = config_hub.config.get_agent(agent_name)
    if not agent_config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found in config")

    updated_fields = []

    if request.enabled is not None:
        agent_config.enabled = request.enabled
        updated_fields.append("enabled")

    if request.llm_override is not None:
        from src.deepnovel.config.models.base import AgentLLMOverride
        agent_config.llm_override = AgentLLMOverride(**request.llm_override)
        updated_fields.append("llm_override")

    if request.tools is not None:
        agent_config.tools = request.tools
        updated_fields.append("tools")

    if request.max_history is not None:
        agent_config.max_history = request.max_history
        updated_fields.append("max_history")

    if request.timeout is not None:
        agent_config.timeout = request.timeout
        updated_fields.append("timeout")

    if request.custom_params is not None:
        agent_config.custom_params.update(request.custom_params)
        updated_fields.append("custom_params")

    return AgentConfigUpdateResponse(
        agent_name=agent_name,
        updated_fields=updated_fields,
        message=f"Agent '{agent_name}' configuration updated: {', '.join(updated_fields)}"
    )


@router.get("/{agent_name}/metrics", response_model=AgentMetricsResponse, summary="获取Agent运行指标")
async def get_agent_metrics(
    agent_name: str,
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """
    获取指定Agent的运行时指标

    - **agent_name**: Agent名称
    """
    metrics = registry.get_agent_metrics(agent_name)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics for agent '{agent_name}' not found")

    return AgentMetricsResponse(
        agent_name=agent_name,
        total_invocations=metrics.get("total_invocations", 0),
        average_duration_ms=metrics.get("average_duration_ms", 0.0),
        success_rate=metrics.get("success_rate", 0.0),
        last_invoked_at=metrics.get("last_invoked_at"),
        error_count=metrics.get("error_count", 0),
    )
```

### 4.4 TaskManagementAPI - 任务管理路由

**职责**: 任务管理接口（列出工作流/暂停/恢复/取消）

```python
# src/deepnovel/api/routes/task.py

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.deepnovel.scheduling import TaskScheduler, TaskState, TaskPriority

router = APIRouter()


# ============================================================================
# 请求/响应模型
# ============================================================================

class TaskListRequest(BaseModel):
    """任务列表查询请求"""
    status: Optional[str] = Field(None, description="按状态过滤")
    workflow_name: Optional[str] = Field(None, description="按工作流名称过滤")
    user_id: Optional[str] = Field(None, description="按用户过滤")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class TaskListItem(BaseModel):
    """任务列表项"""
    task_id: str
    workflow_name: str
    status: str
    priority: str
    progress: float
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    user_id: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class TaskActionRequest(BaseModel):
    """任务操作请求"""
    action: str = Field(..., description="操作: pause/resume/cancel/retry")
    reason: Optional[str] = Field(None, description="操作原因")


class TaskActionResponse(BaseModel):
    """任务操作响应"""
    task_id: str
    action: str
    previous_status: str
    current_status: str
    message: str


class WorkflowDefinitionResponse(BaseModel):
    """工作流定义响应"""
    name: str
    description: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    conditional_edges: List[Dict[str, Any]]


# ============================================================================
# 依赖注入
# ============================================================================

def get_task_scheduler(request: Request) -> TaskScheduler:
    """获取TaskScheduler实例"""
    scheduler = getattr(request.app.state, "task_scheduler", None)
    if not scheduler:
        raise HTTPException(status_code=503, detail="Task scheduler not initialized")
    return scheduler


# ============================================================================
# API端点
# ============================================================================

@router.get("", response_model=TaskListResponse, summary="获取任务列表")
async def list_tasks(
    status: Optional[str] = None,
    workflow_name: Optional[str] = None,
    user_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """
    获取任务列表（支持分页和过滤）

    - **status**: 任务状态过滤 (pending/running/completed/failed/cancelled)
    - **workflow_name**: 工作流名称过滤
    - **user_id**: 用户ID过滤
    - **page**: 页码
    - **page_size**: 每页数量
    """
    task_state = TaskState(status) if status else None

    tasks = scheduler.list_tasks(
        status=task_state,
        user_id=user_id,
        limit=page_size * page  # 先获取足够数据再分页
    )

    # 工作流名称过滤
    if workflow_name:
        tasks = [t for t in tasks if t.workflow_name == workflow_name]

    total = len(tasks)
    start = (page - 1) * page_size
    end = start + page_size
    page_tasks = tasks[start:end]

    return TaskListResponse(
        tasks=[
            TaskListItem(
                task_id=t.task_id,
                workflow_name=t.workflow_name,
                status=t.state.value if hasattr(t.state, "value") else str(t.state),
                priority=TaskPriority(t.sort_key[0]).name if hasattr(TaskPriority, "_value2member_map_") else "NORMAL",
                progress=0.0,  # TODO: 从工作流实例获取
                created_at=isoformat(t.created_at),
                started_at=isoformat(t.started_at) if t.started_at else None,
                completed_at=isoformat(t.completed_at) if t.completed_at else None,
                user_id=t.user_id,
            )
            for t in page_tasks
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total
    )


@router.get("/{task_id}", summary="获取任务详情")
async def get_task_detail(
    task_id: str,
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """
    获取指定任务的详细信息

    - **task_id**: 任务ID
    """
    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {
        "task_id": task.task_id,
        "workflow_name": task.workflow_name,
        "status": task.state.value if hasattr(task.state, "value") else str(task.state),
        "priority": task.priority.value if hasattr(task.priority, "value") else str(task.priority),
        "created_at": isoformat(task.created_at),
        "started_at": isoformat(task.started_at) if task.started_at else None,
        "completed_at": isoformat(task.completed_at) if task.completed_at else None,
        "scheduled_time": isoformat(task.scheduled_time) if task.scheduled_time else None,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "timeout_seconds": task.timeout_seconds,
        "user_id": task.user_id,
        "error_message": task.error_message,
        "workflow_instance_id": task.workflow_instance_id,
        "metadata": task.metadata,
    }


@router.post("/{task_id}/action", response_model=TaskActionResponse, summary="执行任务操作")
async def task_action(
    task_id: str,
    request: TaskActionRequest,
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """
    对指定任务执行操作（暂停/恢复/取消/重试）

    - **task_id**: 任务ID
    - **action**: 操作类型 (pause/resume/cancel/retry)
    - **reason**: 操作原因（可选）
    """
    task = scheduler.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    previous_status = task.state.value if hasattr(task.state, "value") else str(task.state)

    if request.action == "cancel":
        success = await scheduler.cancel(task_id)
        current_status = "cancelled"
        message = f"Task {task_id} cancelled"

    elif request.action == "pause":
        success = await scheduler.pause(task_id)
        current_status = "paused"
        message = f"Task {task_id} paused"

    elif request.action == "resume":
        # 恢复逻辑：重新提交任务
        success = True  # TODO: 实现恢复逻辑
        current_status = "running"
        message = f"Task {task_id} resumed"

    elif request.action == "retry":
        if previous_status not in ("failed", "timeout"):
            raise HTTPException(status_code=400, detail=f"Cannot retry task in {previous_status} state")
        # 重新提交相同任务
        new_task_id = await scheduler.submit(
            workflow_name=task.workflow_name,
            initial_state=task.initial_state,
            priority=task.priority,
            user_id=task.user_id,
        )
        success = True
        current_status = "pending"
        message = f"Task {task_id} retried as {new_task_id}"

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to {request.action} task {task_id}")

    return TaskActionResponse(
        task_id=task_id,
        action=request.action,
        previous_status=previous_status,
        current_status=current_status,
        message=message
    )


@router.get("/workflows/definitions", response_model=List[WorkflowDefinitionResponse], summary="获取工作流定义列表")
async def list_workflow_definitions(
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """
    获取所有已注册的工作流定义（供前端渲染DAG）
    """
    orchestrator = getattr(scheduler, "_workflow_engine", None)
    if not orchestrator:
        raise HTTPException(status_code=503, detail="TaskOrchestrator not available")

    workflows = []
    for name, compiled in orchestrator._workflows.items():
        wf_dict = compiled.graph.to_dict()
        workflows.append(WorkflowDefinitionResponse(
            name=name,
            description=wf_dict.get("description", ""),
            nodes=wf_dict.get("nodes", []),
            edges=wf_dict.get("edges", []),
            conditional_edges=wf_dict.get("conditional_edges", []),
        ))

    return workflows


@router.get("/workflows/definitions/{workflow_name}", response_model=WorkflowDefinitionResponse, summary="获取工作流定义")
async def get_workflow_definition(
    workflow_name: str,
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    """
    获取指定工作流的DAG定义（供前端渲染）

    - **workflow_name**: 工作流名称
    """
    orchestrator = getattr(scheduler, "_workflow_engine", None)
    if not orchestrator:
        raise HTTPException(status_code=503, detail="TaskOrchestrator not available")

    compiled = orchestrator._workflows.get(workflow_name)
    if not compiled:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

    wf_dict = compiled.graph.to_dict()
    return WorkflowDefinitionResponse(
        name=workflow_name,
        description=wf_dict.get("description", ""),
        nodes=wf_dict.get("nodes", []),
        edges=wf_dict.get("edges", []),
        conditional_edges=wf_dict.get("conditional_edges", []),
    )


def isoformat(timestamp: float) -> str:
    """时间戳转ISO格式"""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).isoformat()
```

### 4.5 ConfigAPI - 配置管理路由

**职责**: 配置管理接口（查看配置/热加载/验证）

```python
# src/deepnovel/api/routes/config.py

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.deepnovel.config import ConfigHub

router = APIRouter()


# ============================================================================
# 请求/响应模型
# ============================================================================

class ConfigViewResponse(BaseModel):
    """配置查看响应"""
    key: str
    value: Any
    source: str = Field("runtime", description="配置来源: default/file/env/runtime")
    is_sensitive: bool = Field(False, description="是否为敏感配置")


class ConfigReloadResponse(BaseModel):
    """配置热加载响应"""
    success: bool
    message: str
    changes_detected: int = 0
    changes: List[Dict[str, Any]] = Field(default_factory=list)


class ConfigValidateResponse(BaseModel):
    """配置验证响应"""
    valid: bool
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)


class ConfigHealthResponse(BaseModel):
    """配置健康响应"""
    status: str
    profile: str
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    active_databases: List[str] = Field(default_factory=list)
    llm_providers: List[str] = Field(default_factory=list)
    agents: List[str] = Field(default_factory=list)


# ============================================================================
# 依赖注入
# ============================================================================

def get_config_hub(request: Request) -> ConfigHub:
    """获取ConfigHub实例"""
    hub = getattr(request.app.state, "config_hub", None)
    if not hub or not hub.is_initialized:
        raise HTTPException(status_code=503, detail="ConfigHub not initialized")
    return hub


# ============================================================================
# API端点
# ============================================================================

@router.get("", summary="获取完整配置（脱敏）")
async def get_full_config(
    hub: ConfigHub = Depends(get_config_hub),
):
    """
    获取当前运行时的完整配置（敏感字段已脱敏）

    用于调试和配置审计。
    """
    return hub.config.dump_sensitive_masked()


@router.get("/{key_path:path}", summary="获取指定配置项")
async def get_config_value(
    key_path: str,
    hub: ConfigHub = Depends(get_config_hub),
):
    """
    获取指定配置路径的值

    - **key_path**: 配置路径，如 `llm.default_provider` 或 `database.sqlite.path`
    """
    value = hub.get(key_path)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Config key '{key_path}' not found")

    # 检查是否为敏感字段
    is_sensitive = any(s in key_path.lower() for s in ["password", "secret", "api_key", "token"])

    return ConfigViewResponse(
        key=key_path,
        value="****" if is_sensitive else value,
        source="runtime",
        is_sensitive=is_sensitive,
    )


@router.post("/reload", response_model=ConfigReloadResponse, summary="热加载配置")
async def reload_config(
    hub: ConfigHub = Depends(get_config_hub),
):
    """
    重新加载配置文件（热加载）

    触发ConfigHub重新读取配置文件并验证。
    如果验证失败，保留旧配置不变。
    """
    success = hub.reload()

    if success:
        return ConfigReloadResponse(
            success=True,
            message="Configuration reloaded successfully",
            changes_detected=0,  # TODO: 从reload结果获取变更数
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to reload configuration. Old configuration preserved."
        )


@router.post("/validate", response_model=ConfigValidateResponse, summary="验证当前配置")
async def validate_config(
    hub: ConfigHub = Depends(get_config_hub),
):
    """
    验证当前配置的完整性和一致性

    检查项：
    - 必填字段是否完整
    - LLM提供商配置是否有效
    - 数据库连接配置是否完整
    - Agent配置是否合法
    """
    errors = []
    warnings = []
    config = hub.config

    # 检查LLM配置
    if not config.llm.providers:
        warnings.append({"field": "llm.providers", "message": "No LLM providers configured"})
    else:
        for name, provider in config.llm.providers.items():
            if provider.enabled and not provider.api_key and name != "ollama":
                warnings.append({
                    "field": f"llm.providers.{name}.api_key",
                    "message": f"API key not set for provider '{name}'"
                })

    # 检查数据库配置
    active_dbs = config.database.active_connections
    if not active_dbs:
        warnings.append({"field": "database", "message": "No database connections configured"})

    # 检查Agent配置
    if not config.agents:
        warnings.append({"field": "agents", "message": "No agents configured"})

    # 生产环境检查
    if config.is_production:
        if not config.security.secret_key:
            errors.append({"field": "security.secret_key", "message": "secret_key is required in production"})
        if config.debug:
            errors.append({"field": "debug", "message": "debug must be False in production"})

    return ConfigValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.get("/health", response_model=ConfigHealthResponse, summary="配置健康检查")
async def config_health(
    hub: ConfigHub = Depends(get_config_hub),
):
    """
    获取配置层的健康状态

    检查配置完整性、敏感项、必填项等。
    """
    health = hub.health_check()

    return ConfigHealthResponse(
        status=health.get("status", "unknown"),
        profile=health.get("profile", "unknown"),
        issues=health.get("issues", []),
        active_databases=health.get("active_databases", []),
        llm_providers=health.get("llm_providers", []),
        agents=health.get("agents", []),
    )


@router.get("/schema/{model_name}", summary="获取配置Schema")
async def get_config_schema(
    model_name: str,
    hub: ConfigHub = Depends(get_config_hub),
):
    """
    获取指定配置模型的JSON Schema（供前端动态表单使用）

    - **model_name**: 模型名称 (app/llm/database/agent/novel)
    """
    from src.deepnovel.config.models.base import AppConfig, LLMConfig, DatabaseConfig, AgentConfigModel
    from src.deepnovel.config.models.novel import NovelConfig

    model_map = {
        "app": AppConfig,
        "llm": LLMConfig,
        "database": DatabaseConfig,
        "agent": AgentConfigModel,
        "novel": NovelConfig,
    }

    model_cls = model_map.get(model_name)
    if not model_cls:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found. Available: {list(model_map.keys())}"
        )

    return model_cls.model_json_schema()
```

### 4.6 HealthCheckAPI - 健康检查路由

**职责**: 健康检查接口（含依赖服务状态）

```python
# src/deepnovel/api/routes/health.py

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
import time

from src.deepnovel.config import ConfigHub

router = APIRouter()


# ============================================================================
# 请求/响应模型
# ============================================================================

class ComponentHealth(BaseModel):
    """组件健康状态"""
    name: str
    status: str = Field(..., description="healthy/degraded/unhealthy/unknown")
    response_time_ms: Optional[float] = None
    last_checked: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    overall_status: str = Field(..., description="healthy/degraded/unhealthy")
    version: str
    timestamp: str
    uptime_seconds: Optional[float] = None
    components: List[ComponentHealth]
    summary: Dict[str, int]


class DependencyCheckResponse(BaseModel):
    """依赖服务检查响应"""
    service: str
    status: str
    latency_ms: float
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# 依赖注入
# ============================================================================

def get_config_hub(request: Request) -> ConfigHub:
    """获取ConfigHub实例"""
    hub = getattr(request.app.state, "config_hub", None)
    if not hub or not hub.is_initialized:
        raise HTTPException(status_code=503, detail="ConfigHub not initialized")
    return hub


# ============================================================================
# API端点
# ============================================================================

@router.get("", response_model=HealthCheckResponse, summary="系统健康检查")
async def health_check(
    deep: bool = False,
    request: Request = None,
    hub: ConfigHub = Depends(get_config_hub),
):
    """
    获取系统整体健康状态

    - **deep**: 是否执行深度检查（实际连接测试各依赖服务）

    组件列表：
    - config: 配置系统
    - llm: LLM服务
    - database: 数据库连接
    - vector_store: 向量存储
    - task_scheduler: 任务调度器
    - event_bus: 事件总线
    """
    components = []
    start_time = time.time()

    # 1. 配置系统健康
    config_health = hub.health_check()
    components.append(ComponentHealth(
        name="config",
        status=config_health.get("status", "unknown"),
        last_checked=iso_now(),
        details={
            "profile": config_health.get("profile"),
            "active_databases": config_health.get("active_databases"),
            "llm_providers": config_health.get("llm_providers"),
        }
    ))

    # 2. LLM服务健康
    llm_status = await check_llm_health(hub, deep)
    components.append(llm_status)

    # 3. 数据库健康
    db_status = await check_database_health(hub, deep)
    components.append(db_status)

    # 4. 向量存储健康
    vector_status = await check_vector_store_health(hub, deep)
    components.append(vector_status)

    # 5. 任务调度器健康
    scheduler_status = check_scheduler_health(request)
    components.append(scheduler_status)

    # 6. 事件总线健康
    event_bus_status = check_event_bus_health(request)
    components.append(event_bus_status)

    # 计算总体状态
    overall = "healthy"
    for comp in components:
        if comp.status == "unhealthy":
            overall = "unhealthy"
            break
        elif comp.status == "degraded" and overall == "healthy":
            overall = "degraded"

    healthy_count = sum(1 for c in components if c.status == "healthy")
    degraded_count = sum(1 for c in components if c.status == "degraded")
    unhealthy_count = sum(1 for c in components if c.status == "unhealthy")

    return HealthCheckResponse(
        overall_status=overall,
        version=hub.config.version,
        timestamp=iso_now(),
        uptime_seconds=None,  # TODO: 从应用启动时间计算
        components=components,
        summary={
            "total": len(components),
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
        }
    )


@router.get("/dependencies", response_model=List[DependencyCheckResponse], summary="依赖服务状态检查")
async def check_dependencies(
    hub: ConfigHub = Depends(get_config_hub),
):
    """
    检查所有外部依赖服务的连通性

    检查项：
    - SQLite数据库
    - MySQL数据库（如配置）
    - Neo4j数据库（如配置）
    - MongoDB数据库（如配置）
    - ChromaDB/Qdrant向量存储
    - Ollama/OpenAI LLM服务
    """
    dependencies = []

    # 检查SQLite
    if hub.config.database.sqlite:
        dep = await check_sqlite(hub.config.database.sqlite)
        dependencies.append(dep)

    # 检查MySQL
    if hub.config.database.mysql:
        dep = await check_mysql(hub.config.database.mysql)
        dependencies.append(dep)

    # 检查Neo4j
    if hub.config.database.neo4j:
        dep = await check_neo4j(hub.config.database.neo4j)
        dependencies.append(dep)

    # 检查MongoDB
    if hub.config.database.mongodb:
        dep = await check_mongodb(hub.config.database.mongodb)
        dependencies.append(dep)

    # 检查LLM提供商
    for name, provider in hub.config.llm.providers.items():
        if provider.enabled:
            dep = await check_llm_provider(name, provider)
            dependencies.append(dep)

    return dependencies


@router.get("/component/{component_name}", response_model=ComponentHealth, summary="单个组件健康检查")
async def check_component(
    component_name: str,
    hub: ConfigHub = Depends(get_config_hub),
):
    """
    检查指定组件的健康状态

    - **component_name**: 组件名称 (config/llm/database/vector_store/task_scheduler/event_bus)
    """
    if component_name == "config":
        health = hub.health_check()
        return ComponentHealth(
            name="config",
            status=health.get("status", "unknown"),
            last_checked=iso_now(),
        )

    elif component_name == "llm":
        return await check_llm_health(hub, deep=True)

    elif component_name == "database":
        return await check_database_health(hub, deep=True)

    else:
        raise HTTPException(status_code=404, detail=f"Component '{component_name}' not found")


# ============================================================================
# 辅助检查函数
# ============================================================================

async def check_llm_health(hub: ConfigHub, deep: bool) -> ComponentHealth:
    """检查LLM服务健康"""
    if not deep:
        return ComponentHealth(
            name="llm",
            status="healthy" if hub.config.llm.providers else "degraded",
            last_checked=iso_now(),
        )

    # 深度检查：尝试调用每个启用的提供商
    start = time.time()
    details = {"providers": {}}
    any_healthy = False
    error = None

    for name, provider in hub.config.llm.providers.items():
        if not provider.enabled:
            continue
        try:
            # TODO: 实际调用LLM健康检查
            details["providers"][name] = "healthy"
            any_healthy = True
        except Exception as e:
            details["providers"][name] = f"unhealthy: {str(e)}"
            error = str(e)

    return ComponentHealth(
        name="llm",
        status="healthy" if any_healthy else "unhealthy",
        response_time_ms=(time.time() - start) * 1000,
        last_checked=iso_now(),
        details=details,
        error=error,
    )


async def check_database_health(hub: ConfigHub, deep: bool) -> ComponentHealth:
    """检查数据库健康"""
    active = hub.config.database.active_connections
    if not deep:
        return ComponentHealth(
            name="database",
            status="healthy" if active else "degraded",
            last_checked=iso_now(),
            details={"active_connections": active},
        )

    # 深度检查
    start = time.time()
    # TODO: 实际连接测试
    return ComponentHealth(
        name="database",
        status="healthy",
        response_time_ms=(time.time() - start) * 1000,
        last_checked=iso_now(),
        details={"active_connections": active},
    )


async def check_vector_store_health(hub: ConfigHub, deep: bool) -> ComponentHealth:
    """检查向量存储健康"""
    has_chroma = hub.config.database.chromadb is not None
    return ComponentHealth(
        name="vector_store",
        status="healthy" if has_chroma else "unknown",
        last_checked=iso_now(),
    )


def check_scheduler_health(request: Request) -> ComponentHealth:
    """检查任务调度器健康"""
    scheduler = getattr(request.app.state, "task_scheduler", None)
    if scheduler:
        stats = scheduler.get_stats()
        return ComponentHealth(
            name="task_scheduler",
            status="healthy",
            last_checked=iso_now(),
            details=stats,
        )
    return ComponentHealth(
        name="task_scheduler",
        status="unhealthy",
        last_checked=iso_now(),
        error="TaskScheduler not initialized",
    )


def check_event_bus_health(request: Request) -> ComponentHealth:
    """检查事件总线健康"""
    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        return ComponentHealth(
            name="event_bus",
            status="healthy",
            last_checked=iso_now(),
        )
    return ComponentHealth(
        name="event_bus",
        status="unhealthy",
        last_checked=iso_now(),
        error="EventBus not initialized",
    )


async def check_sqlite(config) -> DependencyCheckResponse:
    """检查SQLite连接"""
    import sqlite3
    start = time.time()
    try:
        conn = sqlite3.connect(config.path)
        conn.execute("SELECT 1")
        conn.close()
        return DependencyCheckResponse(
            service="sqlite",
            status="healthy",
            latency_ms=(time.time() - start) * 1000,
            details={"path": config.path},
        )
    except Exception as e:
        return DependencyCheckResponse(
            service="sqlite",
            status="unhealthy",
            latency_ms=(time.time() - start) * 1000,
            error=str(e),
        )


async def check_mysql(config) -> DependencyCheckResponse:
    """检查MySQL连接（占位）"""
    return DependencyCheckResponse(
        service="mysql",
        status="unknown",
        latency_ms=0,
        details={"host": config.host, "port": config.port},
    )


async def check_neo4j(config) -> DependencyCheckResponse:
    """检查Neo4j连接（占位）"""
    return DependencyCheckResponse(
        service="neo4j",
        status="unknown",
        latency_ms=0,
        details={"uri": config.uri},
    )


async def check_mongodb(config) -> DependencyCheckResponse:
    """检查MongoDB连接（占位）"""
    return DependencyCheckResponse(
        service="mongodb",
        status="unknown",
        latency_ms=0,
        details={"host": config.host, "port": config.port},
    )


async def check_llm_provider(name: str, config) -> DependencyCheckResponse:
    """检查LLM提供商（占位）"""
    return DependencyCheckResponse(
        service=f"llm:{name}",
        status="unknown",
        latency_ms=0,
        details={"provider": name, "model": config.model},
    )


def iso_now() -> str:
    """当前时间ISO格式"""
    from datetime import datetime
    return datetime.now().isoformat()
```

---

## 5. 中间件增强

### 5.1 ConfigAwareMiddleware - ConfigHub集成中间件

```python
# src/deepnovel/api/middleware.py（新增）

class ConfigAwareMiddleware(BaseHTTPMiddleware):
    """
    ConfigHub感知中间件

    将ConfigHub配置注入每个请求的状态，使路由可以方便地获取配置。
    替代旧的直接从settings读取的方式。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 从应用状态获取ConfigHub
        config_hub = getattr(request.app.state, "config_hub", None)
        if config_hub and config_hub.is_initialized:
            request.state.config_hub = config_hub
            request.state.config = config_hub.config

        # 从应用状态获取EventBus
        event_bus = getattr(request.app.state, "event_bus", None)
        if event_bus:
            request.state.event_bus = event_bus

        return await call_next(request)
```

---

## 6. 路由适配示例

### 6.1 旧路由 → 新路由对照

| 旧端点 | 旧实现 | 新端点 | 新实现 |
|--------|--------|--------|--------|
| `POST /tasks` | 直接调用`CoordinatorAgent` | `POST /api/v1/novels/generate` | 提交到`TaskScheduler` |
| `GET /tasks/{id}` | 从内存字典读取 | `GET /api/v1/tasks/{id}` | 从`TaskScheduler`查询 |
| `POST /tasks/{id}/cancel` | 设置内存状态 | `POST /api/v1/tasks/{id}/action` | 调用`scheduler.cancel()` |
| `GET /agents` | 返回硬编码列表 | `GET /api/v1/agents` | 从`AgentRegistry`读取 |
| `GET /health` | 简单返回healthy | `GET /api/v1/health` | 检查所有依赖服务 |
| `POST /config/update` | 操作内存字典 | `POST /api/v1/config/reload` | 调用`ConfigHub.reload()` |
| N/A | N/A | `GET /api/v1/novels/stream/{id}` | SSE实时推送任务状态 |
| N/A | N/A | `GET /api/v1/tasks/workflows/definitions` | 获取工作流DAG定义 |

### 6.2 同步API → 异步API转换示例

**旧实现（同步阻塞）**:
```python
# 旧 routes.py
@router.post("/tasks")
async def create_task(request: TaskCreateRequest, background_tasks: BackgroundTasks):
    # 直接后台执行，无持久化
    background_tasks.add_task(task_controller._execute_task, task_id, request)
    return {"task_id": task_id, "status": "accepted"}
```

**新实现（异步+状态查询）**:
```python
# 新 novel.py
@router.post("/generate")
async def generate_novel(
    request: NovelGenerateRequest,
    scheduler: TaskScheduler = Depends(get_task_scheduler),
):
    # 1. 构建NovelConfig（Step7）
    novel_config = await composer.compose(...)

    # 2. 提交到TaskScheduler（Step5）
    task_id = await scheduler.submit(
        workflow_name="novel_generation",
        initial_state={"novel_config": novel_config.model_dump()},
        priority=TaskPriority.NORMAL,
    )

    # 3. 返回任务ID，客户端通过/status查询
    return NovelGenerateResponse(
        task_id=task_id,
        status="accepted",
        estimated_duration=estimate_duration(...)
    )
```

---

## 7. 与Step1-10的整合

### 7.1 整合矩阵

| Step | 组件 | API层使用方式 | 端点 |
|------|------|-------------|------|
| **Step4** | `DirectorAgent` | 作为工作流入口节点，通过`TaskOrchestrator`调度 | `POST /novels/generate` |
| **Step4** | `AgentRegistry` | 提供Agent列表和状态查询 | `GET /agents`, `GET /agents/{name}` |
| **Step5** | `TaskOrchestrator` | 执行工作流实例 | 内部使用 |
| **Step5** | `TaskScheduler` | 任务队列管理 | `POST /novels/generate`, `GET /tasks/{id}`, `POST /tasks/{id}/action` |
| **Step5** | `EventBus` | SSE流推送状态变更 | `GET /novels/stream/{id}` |
| **Step7** | `ConfigComposer` | 构建NovelConfig | `POST /novels/generate` |
| **Step7** | `NovelConfig` | 作为生成任务输入 | `POST /novels/generate` |
| **Step10** | `ConfigHub` | 统一配置获取 | `GET /config`, `POST /config/reload`, 中间件注入 |
| **Step10** | `AppConfig` | API服务配置（host/port/cors） | `APIGateway.create_app()` |

### 7.2 数据流整合

```
用户请求
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ API Gateway (Step11)                                          │
│  • FastAPI应用工厂                                            │
│  • ConfigHub初始化                                            │
│  • TaskScheduler初始化                                        │
└──────────────────────────────────────────────────────────────┘
    │
    ├──→ NovelGenerationAPI ──→ ConfigComposer (Step7) ──→ NovelConfig
    │                                │
    │                                ▼
    │                         TaskScheduler.submit() (Step5)
    │                                │
    │                                ▼
    │                         TaskOrchestrator.execute() (Step5)
    │                                │
    │                                ▼
    │                         DirectorAgent.process() (Step4)
    │                                │
    │                                ▼
    │                         各Agent节点执行...
    │
    ├──→ AgentManagementAPI ──→ AgentRegistry (Step4)
    │
    ├──→ TaskManagementAPI ──→ TaskScheduler (Step5)
    │
    ├──→ ConfigAPI ──→ ConfigHub (Step10)
    │
    └──→ HealthCheckAPI ──→ 各依赖服务检查
```

---

## 8. 文件结构规划

```
src/deepnovel/api/
├── __init__.py
├── gateway.py                    # API网关 - FastAPI应用工厂（新增）
│   └── APIGateway                # 统一应用创建入口
│
├── routes/                       # 领域路由（按功能拆分）
│   ├── __init__.py
│   ├── novel.py                  # NovelGenerationAPI - 小说生成
│   ├── agent.py                  # AgentManagementAPI - Agent管理
│   ├── task.py                   # TaskManagementAPI - 任务管理
│   ├── config.py                 # ConfigAPI - 配置管理
│   └── health.py                 # HealthCheckAPI - 健康检查
│
├── services/                     # 编排服务层（新增）
│   ├── __init__.py
│   ├── novel_service.py          # 小说生成业务服务
│   ├── agent_service.py          # Agent注册与发现服务
│   ├── task_service.py           # 任务查询与状态聚合服务
│   └── config_service.py         # 配置查询与变更服务
│
├── middleware.py                 # 中间件栈（增强ConfigAwareMiddleware）
├── controllers.py                # 旧控制器（逐步迁移到services/后删除）
├── routes.py                     # 旧路由（逐步迁移到routes/后删除）
└── main.py                       # 旧入口（由gateway.py替代）
```

---

## 9. 实施计划（2周）

### Phase 1: 基础设施搭建（Day 1-3）

```
Day 1: APIGateway + 中间件增强
- 创建 api/gateway.py（FastAPI应用工厂）
- 增强 middleware.py（添加ConfigAwareMiddleware）
- 集成ConfigHub初始化到lifespan
- 集成TaskScheduler启动到lifespan

Day 2: 领域路由骨架
- 创建 api/routes/ 目录
- 创建 novel.py / agent.py / task.py / config.py / health.py 骨架
- 定义所有请求/响应Pydantic模型
- 实现依赖注入函数

Day 3: NovelGenerationAPI
- 实现 POST /novels/generate（集成Step7 ConfigComposer）
- 实现 GET /novels/status/{task_id}
- 实现 GET /novels/result/{task_id}
- 实现 SSE /novels/stream/{task_id}
```

### Phase 2: 核心API实现（Day 4-7）

```
Day 4: TaskManagementAPI
- 实现 GET /tasks（列表查询）
- 实现 GET /tasks/{task_id}（详情）
- 实现 POST /tasks/{task_id}/action（暂停/恢复/取消/重试）
- 实现 GET /workflows/definitions（DAG定义）

Day 5: AgentManagementAPI
- 实现 GET /agents（列表）
- 实现 GET /agents/{name}（详情）
- 实现 PATCH /agents/{name}/config（配置更新）
- 实现 GET /agents/{name}/metrics（指标）

Day 6: ConfigAPI
- 实现 GET /config（完整配置）
- 实现 GET /config/{key_path}（指定项）
- 实现 POST /config/reload（热加载）
- 实现 POST /config/validate（验证）
- 实现 GET /config/schema/{model_name}（Schema）

Day 7: HealthCheckAPI
- 实现 GET /health（系统健康）
- 实现 GET /health/dependencies（依赖服务）
- 实现 GET /health/component/{name}（单个组件）
```

### Phase 3: 集成与迁移（Day 8-10）

```
Day 8: 与Step4/5集成
- 注册NovelGenerationWorkflow到TaskOrchestrator
- 绑定DirectorAgent作为工作流入口节点
- 测试端到端任务提交→执行→完成

Day 9: 旧代码迁移
- 将旧routes.py端点迁移到新routes/目录
- 将旧controllers.py逻辑迁移到services/
- 保持旧API路径兼容（重定向或代理）

Day 10: 前端适配
- 更新前端API调用路径（/api/v1/前缀）
- 实现SSE连接替代轮询
- 添加任务状态实时更新UI
```

### Phase 4: 测试与优化（Day 11-14）

```
Day 11: 单元测试
- API端点单元测试（使用TestClient）
- 依赖注入测试
- Pydantic模型验证测试

Day 12: 集成测试
- 端到端小说生成流程测试
- SSE流测试
- 配置热加载测试

Day 13: 性能优化
- 数据库连接池优化
- SSE广播优化
- 响应缓存（健康检查等）

Day 14: 文档与清理
- OpenAPI文档完善
- 删除旧routes.py和controllers.py
- API使用文档
```

---

## 10. 验收标准

### 10.1 功能验收

| 编号 | 功能 | 测试场景 | 通过标准 |
|------|------|---------|---------|
| F1 | 小说生成提交 | POST /novels/generate | 返回task_id，任务进入队列 |
| F2 | 任务状态查询 | GET /tasks/{id} | 返回正确状态和进度 |
| F3 | SSE状态推送 | 连接/novels/stream/{id} | 实时收到节点状态变更事件 |
| F4 | 任务取消 | POST /tasks/{id}/action (cancel) | 任务状态变为cancelled |
| F5 | Agent列表 | GET /agents | 返回所有可用Agent |
| F6 | Agent配置更新 | PATCH /agents/{name}/config | 配置生效，不重启服务 |
| F7 | 配置热加载 | POST /config/reload | 配置文件变更后API返回新值 |
| F8 | 配置验证 | POST /config/validate | 返回验证错误和警告 |
| F9 | 健康检查 | GET /health?deep=true | 返回所有依赖服务状态 |
| F10 | 工作流定义 | GET /workflows/definitions | 返回可渲染的DAG定义 |
| F11 | ConfigHub集成 | 任意API请求 | 中间件正确注入config_hub |
| F12 | 错误标准化 | 触发各种错误 | 返回统一格式的错误响应 |

### 10.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| API响应时间 | < 200ms (P95) | 1000次请求 |
| 任务提交延迟 | < 100ms | 1000次提交 |
| SSE推送延迟 | < 500ms | 事件产生到客户端接收 |
| 健康检查(快速) | < 50ms | 不包含深度检查 |
| 健康检查(深度) | < 2s | 包含所有依赖连接测试 |
| 并发请求 | >= 100 | 同时100个请求不报错 |

### 10.3 架构验收

| 检查项 | 标准 |
|--------|------|
| 无直接Agent调用 | API层不直接实例化Agent |
| 配置统一入口 | 所有配置通过ConfigHub获取 |
| 异步默认 | 所有耗时操作返回task_id |
| 版本化API | 路径包含/api/v1/前缀 |
| 可观测性 | 每个请求有trace_id和耗时记录 |
| 向后兼容 | 旧端点可重定向到新端点 |

---

## 11. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| 旧API兼容性问题 | 高 | 中 | 保留旧端点1个Sprint，添加弃用警告 |
| SSE连接大量断开 | 中 | 中 | 实现自动重连，降级到轮询 |
| ConfigHub未初始化 | 低 | 高 | 启动时阻塞等待，失败则使用默认配置 |
| TaskScheduler启动失败 | 低 | 高 | 启动时健康检查，失败返回503 |
| 前端适配工作量大 | 中 | 中 | 提供API兼容层，分阶段迁移 |
| Pydantic模型不兼容 | 中 | 中 | 使用model_dump()替代dict() |

---

## 12. 附录

### 12.1 新旧API路径对照表

| 旧路径 | 新路径 | 变更说明 |
|--------|--------|---------|
| `POST /tasks` | `POST /api/v1/novels/generate` | 更明确的语义 |
| `GET /tasks/{id}` | `GET /api/v1/tasks/{id}` | 版本化 |
| `GET /tasks/{id}/health` | `GET /api/v1/health?deep=true` | 合并到统一健康检查 |
| `GET /tasks/{id}/logs` | `GET /api/v1/tasks/{id}` (含logs字段) | 合并到详情 |
| `GET /tasks/{id}/chapters` | `GET /api/v1/novels/result/{id}` | 合并到结果 |
| `POST /tasks/{id}/cancel` | `POST /api/v1/tasks/{id}/action` | 统一操作端点 |
| `GET /tasks` | `GET /api/v1/tasks` | 版本化 |
| `POST /config/update` | `POST /api/v1/config/reload` | 更准确语义 |
| `GET /config/{key}` | `GET /api/v1/config/{key_path}` | 支持嵌套路径 |
| `GET /stats` | `GET /api/v1/tasks` (含stats) | 合并到任务列表 |
| `GET /agents` | `GET /api/v1/agents` | 版本化 |
| `GET /health` | `GET /api/v1/health` | 版本化+增强 |
| N/A | `GET /api/v1/novels/stream/{id}` | 新增SSE |
| N/A | `GET /api/v1/workflows/definitions` | 新增DAG定义 |
| N/A | `GET /api/v1/config/schema/{name}` | 新增Schema |

### 12.2 依赖清单

```
# Python（无新增依赖，使用现有FastAPI + Pydantic）
# FastAPI已包含：Starlette, Pydantic, Uvicorn

# 如需WebSocket支持（可选）
# websockets>=12.0
```

### 12.3 环境变量

```bash
# API服务配置
AINOVELS_API__HOST=0.0.0.0
AINOVELS_API__PORT=8000
AINOVELS_API__CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]

# 工作流配置
AINOVELS_WORKFLOW__MAX_CONCURRENT_TASKS=5
AINOVELS_WORKFLOW__DEFAULT_TIMEOUT=3600
```

---

> **文档结束**
>
> 下一步：按Phase 1开始实施，优先搭建APIGateway和NovelGenerationAPI。
>
> 相关文档：
> - `Step4.md` - Agent层重构（DirectorAgent）
> - `Step5.md` - 任务调度层重构（TaskOrchestrator/TaskScheduler）
> - `Step7.md` - 小说配置补全（ConfigComposer/NovelConfig）
> - `Step10.md` - 配置层重构（ConfigHub）
> - `REVIEW_Step1-10.md` - 综合审查报告（未覆盖区域：API层）

---

*版本: v1.0*
*创建日期: 2026-04-28*
*更新日期: 2026-04-28*
*负责人: Ryan + 小R*
*状态: 设计中*
*预计工期: 14天（2周）*
*依赖: Step4（Agent层）、Step5（任务调度层）、Step7（配置补全层）、Step10（配置层）*
*同步状态: 本地文件（不同步GitHub）*
