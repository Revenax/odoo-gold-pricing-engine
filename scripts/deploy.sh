#!/bin/bash
# Deployment script for EC2 instance
# This script is meant to be run on the EC2 server, not locally
# It performs atomic git pull and basic validation

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
if ! python3 -m py_compile gold_pricing/utils.py; then
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
