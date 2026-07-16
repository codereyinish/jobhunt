#!/bin/bash
# Remove jobhunt's background schedule (both launchd agents).
for label in com.jobhunt.poller com.jobhunt.analyze; do
    plist="$HOME/Library/LaunchAgents/$label.plist"
    launchctl unload "$plist" 2>/dev/null || true
    rm -f "$plist"
    echo "removed $label"
done
