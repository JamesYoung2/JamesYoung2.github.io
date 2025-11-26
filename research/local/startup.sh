#!/bin/bash

echo "Starting Z_n Graph Explorer..."

# Check if DB exists, if not warn user (but server handles it gracefully too)
if [ ! -f "graph_data.db" ]; then
    echo "Warning: graph_data.db not found. Run generator.py to populate data."
fi

# Start the python server in the background
# Using nohup to prevent it from closing immediately if terminal config is weird,
# but standard backgrounding & works for this interactive session.
python3 server.py > server.log 2>&1 &
SERVER_PID=$!

echo "Server started with PID $SERVER_PID on port 47274."
echo "Waiting 2 seconds for server boot..."
sleep 2

# Open the browser
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://127.0.0.1:47274
elif [[ "$OSTYPE" == "darwin"* ]]; then
    open http://127.0.0.1:47274
elif [[ "$OSTYPE" == "msys" ]]; then
    start http://127.0.0.1:47274
else
    echo "Could not detect OS to open browser. Please navigate to http://127.0.0.1:47274"
fi

echo "-----------------------------------"
echo "System is running."
echo "Press ANY KEY to stop the server and exit."
echo "-----------------------------------"

# Wait for user input
read -n 1 -s -r -p ""

# Cleanup
echo ""
echo "Stopping server..."
kill $SERVER_PID
echo "Done."
