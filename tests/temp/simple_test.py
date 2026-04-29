#!/usr/bin/env python
"""
简化版端到端测试
"""

import sys
import os

# 设置项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

def test_ollama_generation():
    """直接测试 Ollama 生成"""
    print("\n" + "="*60)
    print("Test Ollama Content Generation")
    print("="*60)
    
    try:
        from deepnovel.llm.adapters.ollama import OllamaClient
        
        config = {
            "base_url": "http://localhost:11434",
            "model": "qwen2.5-7b",
            "temperature": 0.7,
            "max_tokens": 256
        }
        
        client = OllamaClient(config)
        
        # 测试健康检查
        health = client.health_check()
        print(f"Health check: {health.get('status', 'unknown')}")
        
        if health.get('status') != 'healthy':
            print("Ollama not healthy, skipping generation test")
            return False
        
        # 测试生成
        prompt = "Write one sentence about a magic school:"
        print(f"\nPrompt: {prompt}")
        print("Generating...")
        
        result = client.generate(prompt)
        
        print(f"\nGenerated:")
        print(result[:300])
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_databases():
    """测试数据库连接"""
    print("\n" + "="*60)
    print("Test Database Connections")
    print("="*60)
    
    try:
        from deepnovel.persistence import get_persistence_manager
        
        pm = get_persistence_manager()
        health = pm.health_check()
        
        healthy_count = 0
        for db_name, status in health.items():
            if db_name != "overall":
                db_status = status.get("status", "unknown")
                print(f"  {db_name}: {db_status}")
                if db_status == "healthy":
                    healthy_count += 1
        
        print(f"\nTotal healthy: {healthy_count}")
        return healthy_count >= 5  # 至少5个组件健康
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("AI-Novels Simple Integration Test")
    
    results = {
        "Ollama Generation": test_ollama_generation(),
        "Databases": test_databases(),
    }
    
    print("\n" + "="*60)
    print("Results:")
    print("="*60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED.")
    print("="*60)
    
    sys.exit(0 if all_passed else 1)
