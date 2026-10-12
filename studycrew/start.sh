#!/bin/bash
# StudyCrew startup script

set -e

echo "🚀 Starting StudyCrew..."

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama not running. Please start it with: ollama serve"
    echo "   And pull the model: ollama pull llama3.1:8b"
    exit 1
fi

# Check if model is available
if ! curl -s http://localhost:11434/api/tags | grep -q "llama3.1:8b"; then
    echo "📥 Pulling llama3.1:8b model..."
    ollama pull llama3.1:8b
fi

echo "✅ Ollama ready"

# Start backend
echo "🔧 Starting backend..."
cd backend
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
echo "🎨 Starting frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✨ StudyCrew is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop..."

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT
wait