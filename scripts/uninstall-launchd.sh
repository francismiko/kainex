#!/bin/bash
# Uninstall Kainex Collector launchd service

set -euo pipefail

PLIST_NAME="com.kainex.collector.plist"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

if [ -f "$TARGET" ]; then
    launchctl unload "$TARGET" 2>/dev/null || true
    rm "$TARGET"
    echo "Collector service removed."
else
    echo "Service not installed."
fi
