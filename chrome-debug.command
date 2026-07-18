#!/bin/bash
# ── jobhunt · attach mode ────────────────────────────────────────────────────
# Starts Google Chrome with the DevTools port open so jobhunt's autofill panel can
# attach to your REAL, logged-in browser (instead of launching a separate window).
#
# Double-click this file, then log into Google / LinkedIn / job sites ONCE in the
# window it opens. Keep that Chrome open. Now "Fill application" in jobhunt drops
# the panel straight into it.
#
# Note: modern Chrome only allows the debug port on a NON-default profile, so this
# uses a dedicated profile at ~/.jobhunt-chrome (your everyday Chrome is untouched).
# ─────────────────────────────────────────────────────────────────────────────
PORT="${JOBHUNT_CDP_PORT:-9222}"
PROFILE="$HOME/.jobhunt-chrome"

echo "Opening Chrome with remote debugging on port $PORT"
echo "  profile: $PROFILE"
open -na "Google Chrome" --args \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check

echo
echo "✓ Chrome is up. Log into your sites once, keep this window open,"
echo "  then click 'Fill application' in jobhunt — the panel attaches here."
