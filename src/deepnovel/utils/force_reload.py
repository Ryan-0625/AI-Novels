"""
强制重新加载模块 - 绕过Python缓存机制

使用方法:
    from src.deepnovel.utils.force_reload import force_reload_module
    force_reload_module('src.deepnovel.agents.coordinator')
"""

import sys
import importlib
import os
import time
from typing import Optional


def force_reload_module(module_name: str, verbose: bool = False) -> Optional[object]:
    """
    强制重新加载模块，即使文件没有更改

    Args:
        module_name: 模块名称
        verbose: 是否输出详细信息

    Returns:
        重新加载后的模块对象
    """
    if module_name not in sys.modules:
        if verbose:
            print(f"[ForceReload] Module {module_name} not in sys.modules, trying to import...")
        try:
            module = importlib.import_module(module_name)
            if verbose:
                print(f"[ForceReload] Module {module_name} imported successfully")
            return module
        except Exception as e:
            if verbose:
                print(f"[ForceReload] Failed to import {module_name}: {e}")
            return None

    # 删除模块及其子模块
    modules_to_remove = []
    for name in sys.modules.keys():
        if name == module_name or name.startswith(module_name + "."):
            modules_to_remove.append(name)

    if verbose:
        print(f"[ForceReload] Removing {len(modules_to_remove)} modules from sys.modules")

    for name in modules_to_remove:
        del sys.modules[name]

    # 重新导入
    try:
        module = importlib.import_module(module_name)
        if verbose:
            print(f"[ForceReload] Module {module_name} reloaded successfully")
        return module
    except Exception as e:
        if verbose:
            print(f"[ForceReload] Failed to reload {module_name}: {e}")
        return None


def force_reload_all_deepnovel_modules(verbose: bool = False) -> dict:
    """
    强制重新加载所有 deepnovel 模块

    Args:
        verbose: 是否输出详细信息

    Returns:
        重新加载结果字典
    """
    results = {}
    deepnovel_modules = [
        "src.deepnovel.agents.coordinator",
        "src.deepnovel.agents.agent_communicator",
        "src.deepnovel.agents.base",
        "src.deepnovel.model.message",
        "src.deepnovel.model.agent_config",
        "src.deepnovel.config.manager",
        "src.deepnovel.core.llm_router",
        "src.deepnovel.utils",
    ]

    # 首先删除所有 deepnovel 相关模块
    for name in list(sys.modules.keys()):
        if "deepnovel" in name:
            if verbose:
                print(f"[ForceReload] Removing {name} from sys.modules")
            del sys.modules[name]

    # 重新导入所有模块
    for module_name in deepnovel_modules:
        try:
            module = importlib.import_module(module_name)
            results[module_name] = {"status": "success", "path": getattr(module, "__file__", None)}
            if verbose:
                print(f"[ForceReload] {module_name} loaded from {results[module_name]['path']}")
        except Exception as e:
            results[module_name] = {"status": "error", "message": str(e)}
            if verbose:
                print(f"[ForceReload] Failed to load {module_name}: {e}")

    return results


def get_module_file_path(module_name: str) -> Optional[str]:
    """
    获取模块的文件路径

    Args:
        module_name: 模块名称

    Returns:
        模块文件路径
    """
    if module_name in sys.modules:
        module = sys.modules[module_name]
        return getattr(module, "__file__", None)
    return None


def check_module_is_from_file(module_name: str, expected_path: str) -> bool:
    """
    检查模块是否来自指定文件路径

    Args:
        module_name: 模块名称
        expected_path: 期望的文件路径

    Returns:
        是否匹配
    """
    actual_path = get_module_file_path(module_name)
    if not actual_path:
        return False

    # 规范化路径
    actual_path = os.path.abspath(actual_path)
    expected_path = os.path.abspath(expected_path)

    return actual_path == expected_path


def get_current_module_state() -> dict:
    """
    获取当前模块状态（用于调试）

    Returns:
        模块状态字典
    """
    state = {
        "deepnovel_modules": {},
        "sys_modules_count": len(sys.modules)
    }

    for name in sorted(sys.modules.keys()):
        if "deepnovel" in name or "coordinator" in name:
            module = sys.modules[name]
            state["deepnovel_modules"][name] = {
                "file": getattr(module, "__file__", None),
                "loader": type(getattr(module, "__loader__", None)).__name__
            }

    return state
