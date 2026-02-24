#!/bin/bash
# Runs on the EC2 host via SSH from CI.
# Expects GIT_REPO_PATH (where the repo/module lives on the server).
# Usage: ssh user@host "GIT_REPO_PATH=/opt/odoo/addons/gold_pricing bash -s" < scripts/remote-deploy.sh
# If Odoo binary is not auto-detected from systemd, set it here:
# ODOO_BIN="/path/to/odoo-bin"

set -euo pipefail

if [ -z "${GIT_REPO_PATH:-}" ]; then
  echo "Error: GIT_REPO_PATH not set"
  exit 1
fi

# By default, module name is the directory name at GIT_REPO_PATH (e.g. /opt/odoo/addons/gold_pricing -> gold_pricing).
# Override with MODULE_NAME if you need something else.
MODULE_NAME="${MODULE_NAME:-$(basename "$GIT_REPO_PATH")}"

cd "$GIT_REPO_PATH" || { echo "Error: cannot cd to GIT_REPO_PATH=$GIT_REPO_PATH"; exit 1; }

if [ ! -d .git ]; then
  echo "Error: $GIT_REPO_PATH is not a git repository. On the server run once: git clone <repo-url> $GIT_REPO_PATH"
  exit 1
fi

git fetch origin main
git pull --ff-only origin main || {
  echo "Fast-forward pull failed, trying rebase..."
  git rebase origin/main || {
    echo "Error: Rebase failed. Resolve conflicts or run 'git rebase --abort' and retry."
    exit 1
  }
}

python3 -m py_compile gold_pricing/utils.py || {
  echo "Error: Syntax check failed. Deployment aborted."
  exit 1
}

# Graceful stop: systemctl stop sends SIGTERM so Odoo can finish in-flight requests and
# release DB connections. We then wait for the service to be fully inactive before upgrading.
# Otherwise the running server holds locks and upgrade "sometimes" fails with "lock timeout".
# This isn't bound to happen, but It happenes to me sometimes, failling a couple of tests.
GRACEFUL_STOP_TIMEOUT="${GRACEFUL_STOP_TIMEOUT:-120}"
echo "Stopping Odoo | Graceful with SIGTERM"
sudo systemctl stop odoo || { echo "Error: Odoo stop failed"; exit 1; }
deadline=$(($(date +%s) + GRACEFUL_STOP_TIMEOUT))
while systemctl is-active -q odoo 2>/dev/null; do
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "Warning: Odoo still active after ${GRACEFUL_STOP_TIMEOUT}s, proceeding anyway"
    break
  fi
  echo "  Waiting for Odoo to finish shutting down..."
  sleep 2
done
echo "Odoo stopped."

echo "Upgrading module: $MODULE_NAME"
# Run upgrade the same way systemd does: venv python + odoo-bin (so psycopg2 etc. are available)
ODOO_PYTHON="${ODOO_PYTHON:-}"
ODOO_BIN="${ODOO_BIN:-}"
if [ -z "$ODOO_BIN" ] || [ -z "$ODOO_PYTHON" ] || [ ! -x "$ODOO_BIN" ]; then
  _line=$(systemctl cat odoo 2>/dev/null | grep '^ExecStart=' | sed 's/^ExecStart=//')
  ODOO_PYTHON=$(echo "$_line" | tr ' ' '\n' | grep -E '^/.*/(python3?|python)$' | head -1)
  ODOO_BIN=$(echo "$_line" | tr ' ' '\n' | grep -E '^/.*odoo-bin' | head -1)
  [ -n "$ODOO_BIN" ] || ODOO_BIN=$(echo "$_line" | tr ' ' '\n' | grep -E '^/.*odoo' | grep -v 'venv/bin/python' | grep -v 'bin/python3' | head -1)
fi
if [ -z "$ODOO_BIN" ] || [ ! -x "$ODOO_BIN" ]; then
  echo "Error: Odoo binary not found. On the server run: systemctl cat odoo | grep ExecStart"
  echo "Then set ODOO_BIN (and ODOO_PYTHON if needed) at the top of scripts/remote-deploy.sh."
  sudo systemctl start odoo || true
  exit 1
fi

ODOO_CONFIG="${ODOO_CONFIG:-/etc/odoo.conf}"
UPGRADE_OUTPUT=$(mktemp)
trap 'rm -f "$UPGRADE_OUTPUT"; sudo systemctl start odoo || true' EXIT

set +e
if [ -n "$ODOO_PYTHON" ] && [ -x "$ODOO_PYTHON" ]; then
  sudo -u odoo "$ODOO_PYTHON" "$ODOO_BIN" -u "$MODULE_NAME" --stop-after-init -c "$ODOO_CONFIG" >"$UPGRADE_OUTPUT" 2>&1
else
  sudo -u odoo "$ODOO_BIN" -u "$MODULE_NAME" --stop-after-init -c "$ODOO_CONFIG" >"$UPGRADE_OUTPUT" 2>&1
fi
UPGRADE_EXIT=$?
set -e

if [ "$UPGRADE_EXIT" -ne 0 ]; then
  echo "Error: Odoo upgrade failed (exit $UPGRADE_EXIT). Output:"
  cat "$UPGRADE_OUTPUT"
  exit 1
fi
echo "Module upgraded."

trap - EXIT
echo "Starting Odoo"
sudo systemctl start odoo || { echo "Error: Odoo start failed"; exit 1; }
echo "Odoo started."

echo "Deployment successful."
