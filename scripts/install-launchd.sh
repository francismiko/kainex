#!/bin/bash
# Install Kainex Collector as a launchd service

set -euo pipefail

PLIST_NAME="com.kainex.collector.plist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$SCRIPT_DIR/$PLIST_NAME"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

# Ensure logs directory exists
mkdir -p "$SCRIPT_DIR/../data/logs"

# Unload existing service if present
if launchctl list | grep -q com.kainex.collector; then
    echo "Unloading existing service..."
    launchctl unload "$TARGET" 2>/dev/null || true
fi

cp "$SOURCE" "$TARGET"
launchctl load "$TARGET"
echo "Collector service installed."
echo "Check: launchctl list | grep kainex"
