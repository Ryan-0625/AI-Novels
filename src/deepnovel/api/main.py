"""
FastAPI应用初始化

@file: api/main.py
@date: 2026-03-12
@version: 1.0.0
@description: FastAPI应用初始化和路由注册
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
import os
import sys
import traceback

# 添加src目录到路径
# 使用相对路径以支持 reload 模式下的子进程
cwd = os.getcwd()
src_dir = os.path.join(cwd, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.deepnovel.agents.coordinator import CoordinatorAgent
from src.deepnovel.agents.agent_communicator import AgentCommunicator
from src.deepnovel.model.message import TaskRequest, TaskResponse, TaskStatusUpdate, AgentMessage
from src.deepnovel.utils import log_info, log_error

# 新版配置系统（ConfigHub）
from deepnovel.config.hub import ConfigHub, get_config_hub

# 旧版配置系统（向后兼容，Phase 5 后移除）
from src.deepnovel.config.manager import ConfigManager, settings

# 新版任务编排器（Step 11）
from deepnovel.agents.task_orchestrator import TaskOrchestrator

# 导入控制器
from .controllers import (
    task_controller,
    status_controller,
    config_controller,
    health_controller
)

# 导入旧版路由
from .legacy_routes import router

# Step 11: 新版领域路由
from deepnovel.api.routes import task_router, agent_router, config_router

# 创建FastAPI应用
app = FastAPI(
    title="AI-Novels API",
    description="AI小说生成系统后端API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    log_error(f"Global exception: {exc}")
    log_error(f"Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """验证异常处理"""
    errors = exc.errors()
    log_error(f"Validation error: {errors}")
    return JSONResponse(
        status_code=422,
        content={"detail": errors}
    )

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    log_info("AI-Novels API starting...")

    # 1. 初始化新版 ConfigHub（优先）
    try:
        config_hub = get_config_hub()
        app.state.config_hub = config_hub
        log_info(f"ConfigHub initialized: {config_hub.config.app_version}")
    except Exception as e:
        log_error(f"ConfigHub initialization failed: {e}")

    # 2. 保留旧版 ConfigManager 初始化（向后兼容）
    config_manager = ConfigManager()
    config_paths = [
        "config/system.json",
        "config/database.json",
        "config/llm.json",
        "config/novel_settings.json",
        "config/agents.json",
        "config/messaging.json"
    ]

    existing_paths = [p for p in config_paths if os.path.exists(p)]
    if existing_paths:
        log_info(f"Loading legacy config files: {existing_paths}")
        if config_manager.initialize(existing_paths):
            settings.initialize(config_manager)
            log_info("Legacy ConfigManager initialized")
        else:
            log_error("Failed to initialize legacy ConfigManager")

    # 初始化CoordinatorAgent（不启动通信器以避免阻塞）
    app.state.coordinator = CoordinatorAgent()

    # 3. 初始化 TaskOrchestrator（Step 11）
    try:
        task_orch = TaskOrchestrator(max_workers=4)
        await task_orch.start()
        app.state.task_orchestrator = task_orch
        log_info("TaskOrchestrator initialized with 4 workers")
    except Exception as e:
        log_error(f"TaskOrchestrator initialization failed: {e}")
        # 创建一个最小可用的 orchestrator 避免路由崩溃
        app.state.task_orchestrator = None

    # 通信器将按需初始化，避免启动时阻塞
    # app.state.communicator = AgentCommunicator("api_server")
    # if hasattr(app.state.coordinator, 'start_communication'):
    #     app.state.coordinator.start_communication()

    log_info("AI-Novels API started successfully")

# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    log_info("AI-Novels API shutting down...")

    # 停止通信
    # 通信器按需启动，不需要在关闭时停止
    # if hasattr(app.state, 'coordinator') and hasattr(app.state.coordinator, 'stop_communication'):
    #     app.state.coordinator.stop_communication()

    # 关闭 TaskOrchestrator
    if hasattr(app.state, 'task_orchestrator') and app.state.task_orchestrator is not None:
        try:
            await app.state.task_orchestrator.shutdown()
            log_info("TaskOrchestrator shutdown")
        except Exception as e:
            log_error(f"TaskOrchestrator shutdown error: {e}")

    log_info("AI-Novels API shutdown complete")

# 注册路由
app.include_router(router, prefix="/api/v1")

# Step 11: 新版领域路由（ConfigHub + TaskOrchestrator）
app.include_router(task_router, prefix="/api/v2")
app.include_router(agent_router, prefix="/api/v2")
app.include_router(config_router, prefix="/api/v2")

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "ai-novels-api",
        "version": "1.0.0"
    }

# 根路径
@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI-Novels API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .link { display: block; margin: 10px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; text-decoration: none; color: #007bff; }
            .link:hover { background: #e9e9e9; }
            .status { padding: 10px; background: #d4edda; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>AI-Novels API</h1>
        <div class="status">
            <strong>状态:</strong> 运行中
        </div>
        <p><strong>版本:</strong> 1.0.0</p>
        <h2>API 文档</h2>
        <a href="/docs" class="link"> Swagger UI (交互式文档) </a>
        <a href="/redoc" class="link"> ReDoc 文档 </a>
        <h2>端点</h2>
        <a href="/health" class="link"> 健康检查 </a>
    </body>
    </html>
    """
