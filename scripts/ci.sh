#!/bin/bash
# CI: lint, test, type-check. Run locally or via GitHub Actions.

set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for cmd in ruff pytest mypy; do
  command -v "$cmd" &>/dev/null || { echo "Error: $cmd not found. pip install -r requirements-dev.txt"; exit 1; }
done

ruff check jewellery_evaluator/ tests/
pytest tests/ -v
# Run mypy from inside jewellery_evaluator so the repo root (e.g. odoo-jewellery-evaluator)
# is not treated as a package; mypy rejects directory names with hyphens.
(cd jewellery_evaluator && mypy utils.py --config-file ../pyproject.toml --ignore-missing-imports)
