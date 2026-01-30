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
# Pre-push hook: run same checks as CI (lint, test, type-check)
set -euo pipefail
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
cd "$PROJECT_ROOT"
exec "$PROJECT_ROOT/scripts/ci.sh"
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
