#!/bin/bash

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

echo "Starting Backend..."
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
