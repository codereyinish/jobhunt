#!/bin/bash
# Install jobhunt's background schedule on macOS (launchd). Two agents:
#   • poller  — fetch + prune (close expired) every 2h, notify on new matches
#   • analyze — deep-read up to 40 fresh jobs, 3×/day (09:00 / 15:00 / 21:00)
# Analyze only reads UN-analyzed jobs (afit IS NULL), so it never re-reads a job
# a previous call already screened. Paths are derived from this repo's location.
set -e

REPO="$(cd "$(dirname "$0")/.." && pwd)"       # .../aicode/jobhunt
PARENT="$(dirname "$REPO")"                     # .../aicode  (has the jobhunt pkg)
PY="$REPO/.venv/bin/python"
CLAUDE_DIR="$(dirname "$(command -v claude 2>/dev/null || echo "$HOME/.local/bin/claude")")"
PATH_ENV="$CLAUDE_DIR:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
mkdir -p "$REPO/data"

poller_plist="$HOME/Library/LaunchAgents/com.jobhunt.poller.plist"
cat > "$poller_plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
    <key>Label</key><string>com.jobhunt.poller</string>
    <key>ProgramArguments</key>
    <array><string>$PY</string><string>-m</string><string>jobhunt.cli</string><string>poll</string></array>
    <key>WorkingDirectory</key><string>$PARENT</string>
    <key>EnvironmentVariables</key>
    <dict><key>PYTHONPATH</key><string>$PARENT</string><key>PATH</key><string>$PATH_ENV</string></dict>
    <key>StartInterval</key><integer>7200</integer>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>$REPO/data/poll.log</string>
    <key>StandardErrorPath</key><string>$REPO/data/poll.log</string>
</dict></plist>
EOF

analyze_plist="$HOME/Library/LaunchAgents/com.jobhunt.analyze.plist"
cat > "$analyze_plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
    <key>Label</key><string>com.jobhunt.analyze</string>
    <key>ProgramArguments</key>
    <array><string>$PY</string><string>-m</string><string>jobhunt.cli</string><string>analyze</string><string>--limit</string><string>40</string></array>
    <key>WorkingDirectory</key><string>$PARENT</string>
    <key>EnvironmentVariables</key>
    <dict><key>PYTHONPATH</key><string>$PARENT</string><key>PATH</key><string>$PATH_ENV</string></dict>
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>15</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>0</integer></dict>
    </array>
    <key>StandardOutPath</key><string>$REPO/data/analyze.log</string>
    <key>StandardErrorPath</key><string>$REPO/data/analyze.log</string>
</dict></plist>
EOF

for label in com.jobhunt.poller com.jobhunt.analyze; do
    plist="$HOME/Library/LaunchAgents/$label.plist"
    launchctl unload "$plist" 2>/dev/null || true
    launchctl load "$plist"
done

echo "✓ Scheduled:"
echo "  • poller  — fetch + prune every 2h (log: $REPO/data/poll.log)"
echo "  • analyze — 40 jobs at 09:00 / 15:00 / 21:00 (log: $REPO/data/analyze.log)"
echo "  claude    — using $CLAUDE_DIR/claude"
echo "  Stop  :  bash $REPO/scheduler/uninstall.sh"
