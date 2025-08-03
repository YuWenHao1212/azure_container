#!/bin/bash

# Stop background test execution

echo "Stopping background test execution..."

# Find and kill run_complete_test_suite.sh processes
PIDS=$(ps aux | grep "run_complete_test_suite.sh" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "No test processes found running."
else
    echo "Found test processes: $PIDS"
    for PID in $PIDS; do
        echo "Stopping process $PID..."
        kill $PID
    done
    echo "Test processes stopped."
fi

# Also kill any hanging uvicorn processes from tests
UVICORN_PIDS=$(ps aux | grep "uvicorn src.main:app" | grep -v grep | awk '{print $2}')
if [ ! -z "$UVICORN_PIDS" ]; then
    echo "Cleaning up API server processes..."
    for PID in $UVICORN_PIDS; do
        kill $PID 2>/dev/null
    done
fi

echo "Done."