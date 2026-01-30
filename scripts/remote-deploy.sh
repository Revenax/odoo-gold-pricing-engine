#!/bin/bash
# Runs on the EC2 host via SSH from CI. Expects MODULE_PATH in environment.
# Usage: ssh user@host "MODULE_PATH=/path bash -s" < scripts/remote-deploy.sh

set -euo pipefail

if [ -z "${MODULE_PATH:-}" ]; then
    echo "Error: MODULE_PATH not set"
    exit 1
fi

cd "$MODULE_PATH"

git fetch origin main
git pull --ff-only origin main || {
    echo "Error: Fast-forward pull failed. Deployment aborted."
    exit 1
}

python3 -m py_compile gold_pricing/utils.py || {
    echo "Error: Syntax check failed. Deployment aborted."
    exit 1
}

echo "Deployment successful. Restart Odoo service manually or configure auto-restart."
