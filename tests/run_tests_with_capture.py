#!/usr/bin/env python
"""
运行测试并捕获详细结果
"""
import sys
import os
import json
import time
from datetime import datetime

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

class TestResultCollector:
    """收集测试结果"""
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
        
    def pytest_runtest_setup(self, item):
        """测试设置时记录"""
        self.start_time = time.time()
        
    def pytest_runtest_teardown(self, item):
        """测试清理时记录"""
        pass
        
    def pytest_runtest_logreport(self, report):
        """记录测试结果"""
        if report.when == "call":
            duration = report.duration
            outcome = report.outcome  # passed, failed, skipped
            nodeid = report.nodeid
            
            # 解析测试信息
            parts = nodeid.split("::")
            file_path = parts[0] if parts else ""
            class_name = parts[1] if len(parts) > 1 else ""
            test_name = parts[2] if len(parts) > 2 else (parts[1] if len(parts) > 1 else "")
            
            result = {
                "file": file_path,
                "class": class_name,
                "test": test_name,
                "outcome": outcome,
                "duration": round(duration, 4),
                "timestamp": datetime.now().isoformat()
            }
            
            if outcome == "failed":
                result["error"] = str(report.longrepr) if report.longrepr else "Unknown error"
            
            self.results.append(result)
            
            # 实时打印
            status = "✅" if outcome == "passed" else ("❌" if outcome == "failed" else "⏭️")
            print(f"{status} {test_name} ({duration:.3f}s)")

def main():
    collector = TestResultCollector()
    
    # 测试目录
    test_dirs = [
        "tests/test_core",
        "tests/test_database", 
        "tests/test_agents",
        "tests/test_messaging",
        "tests/test_api",
        "tests/test_api_controllers.py",
        "tests/test_validators.py",
        "tests/test_exceptions.py",
        "tests/test_performance_monitor.py",
        "tests/test_router.py"
    ]
    
    print("=" * 60)
    print("开始执行测试...")
    print("=" * 60)
    
    start_time = time.time()
    
    # 运行测试
    result = pytest.main(
        test_dirs + ["-v", "--tb=short"],
        plugins=[collector]
    )
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # 统计结果
    passed = sum(1 for r in collector.results if r["outcome"] == "passed")
    failed = sum(1 for r in collector.results if r["outcome"] == "failed")
    skipped = sum(1 for r in collector.results if r["outcome"] == "skipped")
    total = len(collector.results)
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"跳过: {skipped}")
    print(f"总耗时: {total_duration:.2f}s")
    print(f"通过率: {passed/total*100:.1f}%" if total > 0 else "N/A")
    
    # 保存结果到文件
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": round(total_duration, 2),
            "pass_rate": round(passed/total*100, 1) if total > 0 else 0
        },
        "results": collector.results
    }
    
    output_file = os.path.join(os.path.dirname(__file__), 'test_real_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细结果已保存到: {output_file}")
    
    return result

if __name__ == "__main__":
    sys.exit(main())
