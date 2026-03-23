#!/bin/bash
# Install Kainex services as launchd agents
# Usage: ./install-launchd.sh [collector|agent|all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$SCRIPT_DIR/../data/logs"

install_service() {
    local name=$1
    local plist="com.kainex.${name}.plist"
    local source="$SCRIPT_DIR/$plist"
    local target="$HOME/Library/LaunchAgents/$plist"

    if [ ! -f "$source" ]; then
        echo "Error: $source not found"
        return 1
    fi

    # Unload existing service if present
    if launchctl list 2>/dev/null | grep -q "com.kainex.${name}"; then
        echo "Unloading existing $name service..."
        launchctl unload "$target" 2>/dev/null || true
    fi

    cp "$source" "$target"
    launchctl load "$target"
    echo "$name service installed."
}

case "${1:-all}" in
    collector)
        install_service collector
        ;;
    agent)
        install_service agent
        ;;
    all)
        install_service collector
        install_service agent
        ;;
    *)
        echo "Usage: $0 [collector|agent|all]"
        exit 1
        ;;
esac

echo "Check: launchctl list | grep kainex"
