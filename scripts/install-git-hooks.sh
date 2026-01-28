#!/bin/bash
# Install git hooks for the project
# This script copies hooks from scripts/hooks/ to .git/hooks/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
HOOKS_SOURCE_DIR="$PROJECT_ROOT/scripts/hooks"

cd "$PROJECT_ROOT"

echo "Installing git hooks..."

# Create hooks directory if it doesn't exist
mkdir -p "$GIT_HOOKS_DIR"

# Copy pre-push hook
if [ -f "$HOOKS_SOURCE_DIR/pre-push" ]; then
    cp "$HOOKS_SOURCE_DIR/pre-push" "$GIT_HOOKS_DIR/pre-push"
    chmod +x "$GIT_HOOKS_DIR/pre-push"
    echo "✓ Installed pre-push hook"
else
    # If hooks directory doesn't exist, create the hook directly
    if [ ! -f "$GIT_HOOKS_DIR/pre-push" ]; then
        cat > "$GIT_HOOKS_DIR/pre-push" << 'HOOK_EOF'
#!/bin/bash
# Pre-push git hook to run linting and tests before allowing push
# Exits with non-zero status if any check fails, preventing the push

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running pre-push checks...${NC}"
echo ""

# Get the project root directory
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"

# Check if dev dependencies are installed
RUFF_AVAILABLE=false
PYTEST_AVAILABLE=false

if command -v ruff &> /dev/null; then
    RUFF_AVAILABLE=true
fi

if command -v pytest &> /dev/null; then
    PYTEST_AVAILABLE=true
fi

# If tools are not installed, warn but allow push (CI will catch it)
if [ "$RUFF_AVAILABLE" = false ] || [ "$PYTEST_AVAILABLE" = false ]; then
    echo -e "${YELLOW}Warning: Development tools not fully installed.${NC}"
    if [ "$RUFF_AVAILABLE" = false ]; then
        echo "  - ruff not found"
    fi
    if [ "$PYTEST_AVAILABLE" = false ]; then
        echo "  - pytest not found"
    fi
    echo ""
    echo "To install: make install-dev"
    echo "To skip checks: git push --no-verify"
    echo ""
    read -p "Continue with push anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Push cancelled."
        exit 1
    fi
    echo "Proceeding with push (CI will run checks)..."
    exit 0
fi

# Optional: check for mypy (don't fail if not installed)
MYPY_AVAILABLE=false
if command -v mypy &> /dev/null; then
    MYPY_AVAILABLE=true
fi

# Run linting
if [ "$RUFF_AVAILABLE" = true ]; then
    echo -e "${YELLOW}1. Running linter (ruff)...${NC}"
    if ! ruff check gold_pricing/ tests/ 2>&1; then
        echo ""
        echo -e "${RED}Linting failed!${NC}"
        echo "Fix linting errors before pushing."
        echo "Run 'ruff check gold_pricing/ tests/' to see detailed errors."
        exit 1
    fi
    echo -e "${GREEN}✓ Linting passed${NC}"
    echo ""
fi

# Run tests
if [ "$PYTEST_AVAILABLE" = true ]; then
    echo -e "${YELLOW}2. Running tests (pytest)...${NC}"
    if ! pytest tests/ -v; then
        echo -e "${RED}Tests failed!${NC}"
        echo "Fix failing tests before pushing."
        exit 1
    fi
    echo -e "${GREEN}✓ Tests passed${NC}"
    echo ""
fi

# Run type checking (optional)
if [ "$MYPY_AVAILABLE" = true ]; then
    echo -e "${YELLOW}3. Running type checker (mypy)...${NC}"
    if ! mypy gold_pricing/utils.py --ignore-missing-imports; then
        echo -e "${RED}Type checking failed!${NC}"
        echo "Fix type errors before pushing."
        exit 1
    fi
    echo -e "${GREEN}✓ Type checking passed${NC}"
    echo ""
fi

echo -e "${GREEN}All pre-push checks passed! Proceeding with push...${NC}"
exit 0
HOOK_EOF
        chmod +x "$GIT_HOOKS_DIR/pre-push"
        echo "✓ Created pre-push hook"
    else
        echo "✓ Pre-push hook already exists"
    fi
fi

echo ""
echo "Git hooks installed successfully!"
echo ""
echo "The pre-push hook will now run automatically before every push."
echo "To skip the hook (not recommended), use: git push --no-verify"
