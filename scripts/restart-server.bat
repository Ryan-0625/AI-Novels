@echo off
cd /d "e:\VScode(study)\Project\AI-Novels"

echo Stopping all uvicorn servers on port 8006...

:: Find and kill processes on port 8006
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8006"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Waiting for processes to terminate...
timeout /t 3 /nobreak >nul

echo Clearing Python cache...
if exist "src\deepnovel\__pycache__" rmdir /s /q "src\deepnovel\__pycache__"
if exist "src\deepnovel\api\__pycache__" rmdir /s /q "src\deepnovel\api\__pycache__"
if exist "src\deepnovel\agents\__pycache__" rmdir /s /q "src\deepnovel\agents\__pycache__"
if exist "src\deepnovel\config\__pycache__" rmdir /s /q "src\deepnovel\config\__pycache__"
if exist "src\deepnovel\core\__pycache__" rmdir /s /q "src\deepnovel\core\__pycache__"
if exist "src\deepnovel\llm\__pycache__" rmdir /s /q "src\deepnovel\llm\__pycache__"
if exist "src\deepnovel\model\__pycache__" rmdir /s /q "src\deepnovel\model\__pycache__"
if exist "src\deepnovel\utils\__pycache__" rmdir /s /q "src\deepnovel\utils\__pycache__"

echoStarting server on port 8006...
python start_server.py
