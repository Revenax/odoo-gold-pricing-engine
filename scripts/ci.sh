#!/bin/bash
# Single CI entrypoint: lint, test, type-check.
# Run locally with ./scripts/ci.sh or via GitHub Actions.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

for cmd in ruff pytest mypy; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: $cmd not found. Run: pip install -r requirements-dev.txt"
        exit 1
    fi
done

echo "1. Linting..."
ruff check gold_pricing/ tests/

echo ""
echo "2. Tests..."
pytest tests/ -v

echo ""
echo "3. Type checking..."
mypy gold_pricing/utils.py --ignore-missing-imports

echo ""
echo "All checks passed."
