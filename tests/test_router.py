#!/usr/bin/env python
"""Test router initialization"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from unittest.mock import Mock, patch


def test_router_initialization():
    """测试LLM路由初始化"""
    from deepnovel.llm.router import get_llm_router
    
    config = {"llm": {"ollama": {"provider": "ollama", "base_url": "http://localhost:11434"}}}
    router = get_llm_router(config, force_init=True)
    
    assert router.is_initialized() is True
    assert "ollama" in router._load_balancer._clients


def test_router_clients():
    """测试路由器客户端列表"""
    from deepnovel.llm.router import get_llm_router
    
    config = {"llm": {"ollama": {"provider": "ollama", "base_url": "http://localhost:11434"}}}
    router = get_llm_router(config, force_init=True)
    
    clients = list(router._load_balancer._clients.keys())
    assert "ollama" in clients


def test_healthy_clients():
    """测试健康客户端列表"""
    from deepnovel.llm.router import get_llm_router
    
    config = {"llm": {"ollama": {"provider": "ollama", "base_url": "http://localhost:11434"}}}
    router = get_llm_router(config, force_init=True)
    
    # 健康客户端列表应该存在（可能为空，取决于Ollama是否运行）
    healthy = router._load_balancer._healthy_clients
    assert isinstance(healthy, list)
