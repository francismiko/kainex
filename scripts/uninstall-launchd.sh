#!/bin/bash
# Uninstall Kainex launchd services
# Usage: ./uninstall-launchd.sh [collector|agent|all]

set -euo pipefail

uninstall_service() {
    local name=$1
    local plist="com.kainex.${name}.plist"
    local target="$HOME/Library/LaunchAgents/$plist"

    if [ -f "$target" ]; then
        launchctl unload "$target" 2>/dev/null || true
        rm "$target"
        echo "$name service removed."
    else
        echo "$name service not installed."
    fi
}

case "${1:-all}" in
    collector)
        uninstall_service collector
        ;;
    agent)
        uninstall_service agent
        ;;
    all)
        uninstall_service collector
        uninstall_service agent
        ;;
    *)
        echo "Usage: $0 [collector|agent|all]"
        exit 1
        ;;
esac
