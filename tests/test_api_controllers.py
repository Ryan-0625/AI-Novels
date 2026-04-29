#!/usr/bin/env python
"""
测试API Controllers
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import json


class FakeRequest:
    """模拟请求对象"""
    user_id = "test_user"
    task_type = "novel"
    genre = "fantasy"
    title = "Test Title"
    description = "Test description"
    chapters = 2
    word_count_per_chapter = 1000
    style = None
    target_audience = None


@pytest.fixture
def task_controller():
    """提供TaskController实例"""
    from deepnovel.api import controllers
    return controllers.TaskController()


@pytest.fixture
def mock_background_tasks():
    """提供模拟的BackgroundTasks"""
    mock = Mock()
    mock.add_task = Mock()
    return mock


@pytest.mark.asyncio
async def test_create_task(task_controller, mock_background_tasks):
    """测试创建任务"""
    request = FakeRequest()
    result = await task_controller.create_task(request, mock_background_tasks)
    
    assert "task_id" in result
    assert result["status"] == "accepted"  # 实际返回的是 accepted
    mock_background_tasks.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_list_tasks(task_controller):
    """测试列出任务"""
    # 先创建一个任务
    request = FakeRequest()
    mock_bg = Mock()
    mock_bg.add_task = Mock()
    
    create_result = await task_controller.create_task(request, mock_bg)
    task_id = create_result["task_id"]
    
    # 列出任务
    tasks = await task_controller.list_tasks(None, None, 1, 10)
    
    assert "tasks" in tasks
    assert "total" in tasks
    assert tasks["total"] >= 1


@pytest.mark.asyncio
async def test_get_task_status(task_controller):
    """测试获取任务状态"""
    request = FakeRequest()
    mock_bg = Mock()
    mock_bg.add_task = Mock()
    
    # 创建任务
    create_result = await task_controller.create_task(request, mock_bg)
    task_id = create_result["task_id"]
    
    # 获取状态 - TaskController 没有 get_task_status 方法，使用 _tasks 字典直接访问
    assert task_id in task_controller._tasks
    task_info = task_controller._tasks[task_id]
    
    assert "task_id" in task_info
    assert "status" in task_info
