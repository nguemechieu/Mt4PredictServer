#!/bin/bash
echo "🚀 Starting MetaTrader 4 under Wine..."

MT4_PATH="$HOME/.wine/drive_c/Program Files/MetaTrader 4/terminal.exe"

# Fallback if path is different
if [ ! -f "$MT4_PATH" ]; then
    MT4_PATH=$(find "$HOME/.wine/drive_c/" -name "terminal.exe" | head -n 1)
fi

if [ -z "$MT4_PATH" ]; then
    echo "❌ MT4 terminal.exe not found!"
    exit 1
fi

echo "✅ MT4 located at: $MT4_PATH"

# Start Xvfb virtual display for GUI
Xvfb :0 -screen 0 1024x768x16 &
sleep 3

# Run MetaTrader 4
wine "$MT4_PATH" &
MT4_PID=$!

# Wait for it to initialize
sleep 10

echo "✅ MT4 running (PID $MT4_PID)"
wait $MT4_PID
