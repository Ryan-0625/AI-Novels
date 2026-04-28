"""
添加src目录到路径 - 使用相对于 CWD 的路径
"""
import sys
import os

# 获取当前工作目录
cwd = os.getcwd()
src_dir = os.path.join(cwd, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
    print(f"Added {src_dir} to sys.path")
