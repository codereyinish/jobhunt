#!/bin/bash
# Install the jobhunt 24/7 poller on macOS (launchd). Polls every 20 min and
# sends a desktop notification on fresh high-score matches. Portable — paths
# are derived from this repo's location.
set -e

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"
LABEL="com.jobhunt.poller"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PY</string>
        <string>-m</string><string>jobhunt.cli</string><string>poll</string>
    </array>
    <key>WorkingDirectory</key><string>$REPO</string>
    <key>StartInterval</key><integer>1200</integer>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>$REPO/data/poll.log</string>
    <key>StandardErrorPath</key><string>$REPO/data/poll.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Loaded $LABEL — polls every 20 min."
echo "  Logs : tail -f $REPO/data/poll.log"
echo "  Stop : launchctl unload $PLIST"
