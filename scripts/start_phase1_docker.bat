@echo off
REM ======================================================
REM AI-Novels Phase 1 — Docker 中间件 + 全服务启动脚本
REM 适用: Windows 宿主机 (PowerShell)
REM 用法: 以管理员身份运行此脚本
REM ======================================================

cd /d E:\VScode(study)\Project\AI-Novels

echo ========================================
echo  AI-Novels Phase 1 全栈启动
echo ========================================

REM ──────────────────────────────────────────
REM Step 1: Docker 中间件启动
REM ──────────────────────────────────────────
echo [1/5] 启动 Docker 中间件...

REM 检查 Docker 运行状态
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker 未运行, 请先启动 Docker Desktop
    pause
    exit /b 1
)

REM 启动 PostgreSQL + Redis + ChromaDB
docker compose up -d postgres 2>nul
docker compose up -d redis 2>nul
docker compose up -d chromadb 2>nul

REM 等待 PostgreSQL 就绪
echo [WAIT] 等待 PostgreSQL 就绪...
:wait_pg
timeout /t 2 /nobreak >nul
docker compose exec postgres pg_isready -U ai_novels >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto wait_pg
echo [OK] PostgreSQL 就绪

REM ──────────────────────────────────────────
REM Step 2: 创建数据库 (如不存在)
REM ──────────────────────────────────────────
echo [2/5] 检查数据库...
docker compose exec postgres psql -U ai_novels -tc "SELECT 1 FROM pg_database WHERE datname='ai_novels'" 2>nul | find "1" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] 创建数据库 ai_novels...
    docker compose exec postgres createdb -U ai_novels ai_novels
)
echo [OK] 数据库就绪

REM ──────────────────────────────────────────
REM Step 3: Python 依赖检查
REM ──────────────────────────────────────────
echo [3/5] 检查 Python 依赖...
python -c "import fastapi; import uvicorn; import sqlalchemy; import alembic" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] 安装依赖...
    pip install -r requirements.txt
    pip install bcrypt pyjwt redis asyncpg chromadb httpx
)
echo [OK] 依赖就绪

REM ──────────────────────────────────────────
REM Step 4: 数据库迁移
REM ──────────────────────────────────────────
echo [4/5] 执行数据库迁移...
alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] 自动迁移失败, 尝试手动初始化...
    alembic revision --autogenerate -m "initial_schema" 2>nul
    alembic upgrade head
)
echo [OK] 迁移完成

REM ──────────────────────────────────────────
REM Step 5: 启动 FastAPI 服务
REM ──────────────────────────────────────────
echo [5/5] 启动 FastAPI 服务...
echo.
echo ========================================
echo  AI-Novels 服务已就绪
echo  API 文档:      http://localhost:28004/docs
echo  Redoc:         http://localhost:8004/redoc
echo  健康检查:       http://localhost:8004/health
echo  SSE 事件流:     http://localhost:8004/api/v2/events
echo  认证注册:       POST /api/v2/auth/register
echo  认证登录:       POST /api/v2/auth/login
echo ========================================
echo.

uvicorn src.ai_novels.api.main:app --host 0.0.0.0 --port 28004 --reload

pause
