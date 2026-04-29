"""
任务管理API路由

Step 11: 任务管理接口（列出任务/查询状态/暂停/恢复/取消）
基于 TaskOrchestrator 实现

@file: api/routes/task_routes.py
@date: 2026-04-29
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from deepnovel.api.dependencies import get_config_hub_dep
from deepnovel.config.hub import ConfigHub

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ---- 请求/响应模型 ----


class TaskListItem(BaseModel):
    """任务列表项"""

    task_id: str
    agent_name: str
    status: str
    priority: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""

    tasks: List[TaskListItem]
    total: int


class TaskDetailResponse(BaseModel):
    """任务详情响应"""

    task_id: str
    agent_name: str
    status: str
    priority: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskActionRequest(BaseModel):
    """任务操作请求"""

    action: str = Field(..., description="操作: pause/resume/cancel")


class TaskActionResponse(BaseModel):
    """任务操作响应"""

    task_id: str
    action: str
    success: bool
    message: str


class WorkflowDefResponse(BaseModel):
    """工作流定义响应"""

    name: str
    description: str
    stages: List[str]


# ---- 依赖注入 ----


def get_task_orchestrator(request: Request):
    """获取 TaskOrchestrator 实例"""
    orch = getattr(request.app.state, "task_orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=503, detail="TaskOrchestrator not initialized")
    return orch


# ---- API 端点 ----


@router.get("", response_model=TaskListResponse, summary="获取任务列表")
async def list_tasks(
    orchestrator=Depends(get_task_orchestrator),
):
    """列出所有任务状态"""
    stats = orchestrator.get_stats()
    workers = stats.get("workers", {})
    queued = stats.get("queued_tasks", 0)
    completed = stats.get("completed", 0)

    tasks = []
    for name, info in workers.items():
        tasks.append(
            TaskListItem(
                task_id=info.get("current_task") or "idle",
                agent_name=name,
                status="running" if not info.get("idle", True) else "idle",
                priority="normal",
                created_at="",
            )
        )

    return TaskListResponse(tasks=tasks, total=len(tasks) + queued + completed)


@router.get("/{task_id}", response_model=TaskDetailResponse, summary="获取任务详情")
async def get_task_detail(
    task_id: str,
    orchestrator=Depends(get_task_orchestrator),
):
    """获取指定任务的详细信息"""
    result = orchestrator.get_result_nowait(task_id)
    if result is not None:
        return TaskDetailResponse(
            task_id=task_id,
            agent_name="",
            status="completed",
            priority="normal",
            result=result if isinstance(result, dict) else {"output": str(result)},
        )

    # 任务仍在队列中
    return TaskDetailResponse(
        task_id=task_id,
        agent_name="",
        status="pending",
        priority="normal",
    )


@router.post("/{task_id}/action", response_model=TaskActionResponse, summary="执行任务操作")
async def task_action(
    task_id: str,
    req: TaskActionRequest,
    orchestrator=Depends(get_task_orchestrator),
):
    """对任务执行操作（暂停/恢复/取消）"""
    # TaskOrchestrator 当前版本不支持暂停/恢复，返回友好提示
    return TaskActionResponse(
        task_id=task_id,
        action=req.action,
        success=False,
        message=f"Action '{req.action}' not yet supported in this version",
    )


@router.get("/workflows/definitions", response_model=List[WorkflowDefResponse], summary="获取工作流定义列表")
async def list_workflows(
    hub: ConfigHub = Depends(get_config_hub_dep),
):
    """列出所有已注册的工作流定义"""
    orch = getattr(hub, "_orchestrator", None)
    if orch is None:
        # 返回默认工作流
        return [
            WorkflowDefResponse(
                name="novel_generation",
                description="小说生成完整工作流",
                stages=["需求分析", "大纲规划", "角色生成", "世界构建", "内容生成", "质量检查", "文本润色"],
            )
        ]
    workflows = orch.list_workflows() if hasattr(orch, "list_workflows") else []
    return [
        WorkflowDefResponse(
            name=w.get("name", "unknown"),
            description=w.get("description", ""),
            stages=w.get("stages", []),
        )
        for w in workflows
    ]
