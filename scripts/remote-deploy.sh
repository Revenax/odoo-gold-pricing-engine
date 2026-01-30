#!/bin/bash
# Runs on the EC2 host via SSH from CI.
# Expects GIT_REPO_PATH (where to git pull) and DEPLOY_TARGET (where Odoo expects the module).
# Usage: ssh user@host "GIT_REPO_PATH=/path/to/repo DEPLOY_TARGET=/path/to/gold_pricing bash -s" < scripts/remote-deploy.sh

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

if [ -n "${ODOO_RESTART_CMD:-}" ]; then
  echo "Restarting Odoo: $ODOO_RESTART_CMD"
  eval "$ODOO_RESTART_CMD" || { echo "Error: Odoo restart failed"; exit 1; }
  echo "Odoo restarted."
else
  echo "Odoo restart skipped (ODOO_RESTART_CMD not set). Restart manually if needed."
fi

echo "Deployment successful."
