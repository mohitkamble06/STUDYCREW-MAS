@echo off
REM StudyCrew startup script for Windows

echo 🚀 Starting StudyCrew...

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Ollama not running. Please start it with: ollama serve
    echo    And pull the model: ollama pull llama3.1:8b
    pause
    exit /b 1
)

echo ✅ Ollama ready

REM Start backend
echo 🔧 Starting backend...
cd backend
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
alembic upgrade head
start "StudyCrew Backend" cmd /k "uvicorn app.main:app --reload --port 8000"
cd ..

REM Start frontend
echo 🎨 Starting frontend...
cd frontend
if not exist "node_modules" (
    npm install
)
start "StudyCrew Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ✨ StudyCrew is running!
echo    Frontend: http://localhost:5173
echo    Backend API: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C in each window to stop...
pause