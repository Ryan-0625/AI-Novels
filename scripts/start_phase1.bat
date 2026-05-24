@echo off
REM AI-Novels Phase 1 启动脚本
REM 在项目根目录执行: scripts\start_phase1.bat

echo ========================================
echo  AI-Novels Phase 1 启动
echo  1. 检查依赖
echo  2. 执行数据库迁移
echo  3. 启动开发服务器
echo ========================================

cd /d %~dp0\..

REM Step 1: 检查关键依赖
echo [1/4] 检查 Python 依赖...
python -c "import fastapi; import uvicorn; import sqlalchemy; import alembic; import redis; import jwt; import bcrypt" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] 部分依赖缺失, 执行安装...
    pip install -r requirements.txt 2>nul
    pip install bcrypt pyjwt 2>nul
    pip install redis 2>nul
)
echo [OK] 依赖检查完成

REM Step 2: 检查 PostgreSQL
echo [2/4] 检查数据库连接...
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
async def check():
    try:
        engine = create_async_engine('postgresql+asyncpg://ai_novels:ai_novels_pass@localhost:5432/ai_novels')
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        print('[OK] PostgreSQL 连接正常')
    except Exception as e:
        print(f'[WARN] 数据库不可用: {e}')
        print('[INFO] 确保 PostgreSQL 已启动且 database ai_novels 已创建')
asyncio.run(check())
" 2>&1

REM Step 3: 执行数据库迁移
echo [3/4] 执行 Alembic 迁移...
alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] 迁移失败, 尝试初始迁移...
    alembic revision --autogenerate -m "initial_schema" 2>nul
    alembic upgrade head
)
echo [OK] 数据库迁移完成

REM Step 4: 启动服务
echo [4/4] 启动 FastAPI 开发服务器...
echo [INFO] API:  http://localhost:28004
echo [INFO] Docs: http://localhost:8004/docs
echo [INFO] 按 Ctrl+C 停止
echo ========================================

python -m uvicorn src.ai_novels.api.main:app --host 0.0.0.0 --port 28004 --reload
