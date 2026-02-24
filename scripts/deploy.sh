#!/bin/bash
# Deployment script for EC2 instance (run on the server).
# Performs atomic git pull and syntax validation only.
# For full deploy (build flat module at addons path and run Odoo upgrade), use scripts/remote-deploy.sh via scripts/deploy-local.sh.

set -euo pipefail

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Starting deployment..."

# Ensure we're on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Warning: Not on main branch (current: $CURRENT_BRANCH)"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
fi

# Fetch latest changes
echo "Fetching latest changes..."
git fetch origin main

# Atomic pull - only fast-forward to ensure we're on a clean commit
echo "Pulling latest changes (fast-forward only)..."
if ! git pull --ff-only origin main; then
    echo "Error: Fast-forward pull failed. This means:"
    echo "  - Local changes exist that aren't in remote"
    echo "  - Or remote has diverged from local"
    echo ""
    echo "Deployment aborted. Please resolve conflicts manually."
    exit 1
fi

# Quick syntax validation
echo "Validating Python syntax..."
if ! python3 -m py_compile jewellery_evaluator/utils.py; then
    echo "Error: Syntax validation failed. Deployment aborted."
    exit 1
fi

echo ""
echo "Deployment successful!"
echo "Current commit: $(git rev-parse --short HEAD)"
echo ""
echo "Next steps:"
echo "  1. Restart Odoo service (method depends on your setup)"
echo "  2. Verify module is working correctly"
echo ""
echo "Example restart commands:"
echo "  - systemd: sudo systemctl restart odoo"
echo "  - screen/tmux: Find your Odoo process and restart it"
