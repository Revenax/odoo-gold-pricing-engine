#!/bin/bash
# Runs on the EC2 host via SSH from CI.
# Expects GIT_REPO_PATH (where to git pull) and DEPLOY_TARGET (where Odoo expects the module).
# Usage: ssh user@host "GIT_REPO_PATH=/path/to/repo DEPLOY_TARGET=/path/to/gold_pricing bash -s" < scripts/remote-deploy.sh
# If Odoo binary is not auto-detected from systemd, set it here:
# ODOO_BIN="/path/to/odoo-bin"

set -euo pipefail

if [ -z "${GIT_REPO_PATH:-}" ]; then
  echo "Error: GIT_REPO_PATH not set"
  exit 1
fi
if [ -z "${DEPLOY_TARGET:-}" ]; then
  echo "Error: DEPLOY_TARGET not set"
  exit 1
fi

cd "$GIT_REPO_PATH" || { echo "Error: cannot cd to GIT_REPO_PATH=$GIT_REPO_PATH"; exit 1; }

if [ ! -d .git ]; then
  echo "Error: $GIT_REPO_PATH is not a git repository. On the server run once: git clone <repo-url> $GIT_REPO_PATH"
  exit 1
fi

git fetch origin main
git pull --ff-only origin main || {
  echo "Error: Fast-forward pull failed. Deployment aborted."
  exit 1
}

python3 -m py_compile gold_pricing/utils.py || {
  echo "Error: Syntax check failed. Deployment aborted."
  exit 1
}

# Copy module to where Odoo expects it when repo path != deploy target (e.g. repo is odoo-gold-pricing-engine, module is gold_pricing)
if [ "$GIT_REPO_PATH" != "$DEPLOY_TARGET" ]; then
  rm -rf "$DEPLOY_TARGET"
  cp -a "$GIT_REPO_PATH/gold_pricing" "$(dirname "$DEPLOY_TARGET")/"
fi

echo "Upgrading module: gold_pricing"
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
  exit 1
fi
if [ -n "$ODOO_PYTHON" ] && [ -x "$ODOO_PYTHON" ]; then
  sudo -u odoo "$ODOO_PYTHON" "$ODOO_BIN" -u gold_pricing --stop-after-init -c /etc/odoo.conf || { echo "Error: Odoo upgrade failed"; exit 1; }
else
  sudo -u odoo "$ODOO_BIN" -u gold_pricing --stop-after-init -c /etc/odoo.conf || { echo "Error: Odoo upgrade failed"; exit 1; }
fi
echo "Module upgraded."

echo "Restarting Odoo"
sudo systemctl restart odoo || { echo "Error: Odoo restart failed"; exit 1; }
echo "Odoo restarted."

echo "Deployment successful."
