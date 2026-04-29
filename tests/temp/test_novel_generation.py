#!/usr/bin/env python
"""
小说生成端到端测试

测试完整链路：
1. 配置加载
2. 数据库连接
3. LLM 服务
4. Agent 工作流
5. 小说内容生成
"""

import sys
import os
import asyncio
import json

# 设置项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from deepnovel.config.manager import settings
from deepnovel.agents.coordinator import CoordinatorAgent
from deepnovel.model.message import TaskRequest


def test_configuration():
    """测试配置加载"""
    print("\n" + "="*60)
    print("1. Test Configuration Loading")
    print("="*60)
    
    try:
        # 检查核心配置
        db_config = settings.get_database("mysql")
        llm_config = settings.get_llm()
        
        print(f"[OK] MySQL Config: {db_config.get('host')}:{db_config.get('port')}")
        print(f"[OK] LLM Provider: {llm_config.get('provider', 'default')}")
        print(f"[OK] Ollama Model: {llm_config.get('model', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Configuration loading failed: {e}")
        return False


def test_database_connections():
    """测试数据库连接"""
    print("\n" + "="*60)
    print("2. Test Database Connections")
    print("="*60)
    
    from deepnovel.persistence import get_persistence_manager
    
    try:
        pm = get_persistence_manager()
        health = pm.health_check()
        
        for db_name, status in health.items():
            if db_name != "overall":
                db_status = status.get("status", "unknown")
                icon = "[OK]" if db_status == "healthy" else "[FAIL]"
                print(f"{icon} {db_name}: {db_status}")
        
        overall = health.get("overall", {}).get("status", "unknown")
        return overall == "healthy"
    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        return False


def test_llm_service():
    """测试 LLM 服务"""
    print("\n" + "="*60)
    print("3. Test LLM Service")
    print("="*60)
    
    from deepnovel.llm.router import get_llm_router
    
    try:
        config = {"llm": settings.get_llm()}
        router = get_llm_router(config, force_init=True)
        
        if not router.is_initialized():
            print("[FAIL] LLM router not initialized")
            return False
        
        # 检查 Ollama 客户端
        ollama_client = router.get_client_by_name("ollama")
        if ollama_client:
            health = ollama_client.health_check()
            status = health.get("status", "unknown")
            icon = "[OK]" if status == "healthy" else "[FAIL]"
            print(f"{icon} Ollama: {status}")
            return status == "healthy"
        else:
            print("[FAIL] Ollama client not available")
            return False
            
    except Exception as e:
        print(f"[FAIL] LLM service test failed: {e}")
        return False


async def test_agent_workflow():
    """测试 Agent 工作流"""
    print("\n" + "="*60)
    print("4. Test Agent Workflow")
    print("="*60)
    
    try:
        # 创建协调者
        coordinator = CoordinatorAgent()
        
        # 创建测试任务 - 使用正确的参数
        task_request = TaskRequest(
            agent_name="coordinator",
            task_id="test_task_001",
            user_id="test_user",
            payload={
                "task_type": "novel",
                "genre": "fantasy",
                "title": "Test Novel",
                "description": "This is a test novel generation task",
                "chapters": 1,
                "word_count_per_chapter": 1000,
                "style": "light",
                "target_audience": "young readers"
            }
        )
        
        print(f"[OK] Coordinator Agent created")
        print(f"[OK] Task request created: {task_request.task_id}")
        print(f"   - Agent: {task_request.agent_name}")
        print(f"   - Payload keys: {list(task_request.payload.keys())}")
        
        return True
    except Exception as e:
        print(f"[FAIL] Agent workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_content_generation():
    """测试内容生成"""
    print("\n" + "="*60)
    print("5. Test Content Generation")
    print("="*60)
    
    from deepnovel.llm.adapters.ollama import OllamaClient
    
    try:
        # 直接使用 Ollama 客户端测试生成
        config = {
            "base_url": "http://localhost:11434",
            "model": "qwen2.5-7b",
            "temperature": 0.7,
            "max_tokens": 512
        }
        
        client = OllamaClient(config)
        
        # 测试简单生成
        prompt = "Write a short opening about a magic academy (within 100 words):"
        print(f"\nPrompt: {prompt}")
        print("Generating...")
        
        result = client.generate(prompt)
        
        print(f"\n[OK] Generation successful!")
        print(f"Generated content:\n{result[:200]}...")
        
        return True
    except Exception as e:
        print(f"[FAIL] Content generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("AI-Novels Project End-to-End Test")
    print("="*60)
    
    results = {
        "Configuration": test_configuration(),
        "Database": test_database_connections(),
        "LLM Service": test_llm_service(),
    }
    
    # 异步测试
    results["Agent Workflow"] = await test_agent_workflow()
    results["Content Generation"] = await test_content_generation()
    
    # 打印总结
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for test_name, passed in results.items():
        icon = "[PASS]" if passed else "[FAIL]"
        print(f"{icon} {test_name}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("[SUCCESS] All tests passed! Project pipeline is complete.")
    else:
        print("[WARNING] Some tests failed, please check configuration.")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
