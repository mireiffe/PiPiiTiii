#!/bin/bash

# Default port
PORT=${1:-8000}
export BACKEND_PORT=$PORT
export VITE_API_PORT=$PORT

echo "Using Backend Port: $PORT"

# Function to kill processes on exit
cleanup() {
    echo "Stopping processes..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID
    fi
    exit
}

trap cleanup SIGINT SIGTERM

# Kill existing processes on ports
echo "Checking for existing processes..."

# Kill process on selected port (Backend)
PORT_PID=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$PORT_PID" ]; then
    echo "Killing process on port $PORT (PID: $PORT_PID)..."
    kill -9 $PORT_PID 2>/dev/null
    sleep 1
fi

# Kill process on port 5173 (Frontend - Vite default)
PORT_5173_PID=$(lsof -ti:5173 2>/dev/null)
if [ -n "$PORT_5173_PID" ]; then
    echo "Killing process on port 5173 (PID: $PORT_5173_PID)..."
    kill -9 $PORT_5173_PID 2>/dev/null
    sleep 1
fi

echo "Starting Backend on port $PORT..."
if [ -f ".venv/Scripts/python" ]; then
    PYTHON=".venv/Scripts/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi

$PYTHON backend/main.py &
BACKEND_PID=$!

echo "Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!

# Wait for processes
wait
