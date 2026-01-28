#!/bin/bash
# Pre-deployment check script for gold_pricing module
# Exits with non-zero status if any check fails

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Running pre-deployment checks..."
echo ""

# Check if dev dependencies are installed
if ! command -v ruff &> /dev/null; then
    echo "Error: ruff not found. Run 'make install-dev' or 'pip install -r requirements-dev.txt'"
    exit 1
fi

if ! command -v pytest &> /dev/null; then
    echo "Error: pytest not found. Run 'make install-dev' or 'pip install -r requirements-dev.txt'"
    exit 1
fi

if ! command -v mypy &> /dev/null; then
    echo "Error: mypy not found. Run 'make install-dev' or 'pip install -r requirements-dev.txt'"
    exit 1
fi

# Run checks
echo "1. Running linter..."
ruff check gold_pricing/ tests/ || {
    echo "Linting failed!"
    exit 1
}

echo ""
echo "2. Running tests..."
pytest tests/ -v || {
    echo "Tests failed!"
    exit 1
}

echo ""
echo "3. Running type checker..."
mypy gold_pricing/utils.py --ignore-missing-imports || {
    echo "Type checking failed!"
    exit 1
}

echo ""
echo "All checks passed! Ready for deployment."
