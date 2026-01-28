# Contributing Guidelines

## Code Standards

### Python Code Style

- Follow PEP 8 style guidelines
- Use `ruff` for linting (configured in `pyproject.toml`)
- All Python files must have UTF-8 encoding header: `# -*- coding: utf-8 -*-`
- All files must include copyright header

### Import Organization

1. Standard library imports
2. Third-party imports (e.g., `odoo`, `requests`)
3. Local application imports (relative imports with `..`)

Example:
```python
import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from ..utils import compute_gold_product_price
```

### Logging

- Use module-level logger: `_logger = logging.getLogger(__name__)`
- Import logging at the top of the file, not inside functions
- Use appropriate log levels:
  - `_logger.error()` for errors
  - `_logger.warning()` for warnings
  - `_logger.info()` for informational messages

### Error Handling

- Use `ValidationError` for user-facing validation errors
- Use `ValueError` for programming errors or API issues
- Always provide clear, actionable error messages
- Never log sensitive information (API cookies, passwords, etc.)

### Type Hints

- Add type hints to pure helper functions in `utils.py`
- Use `tuple[float, float, float]` syntax (Python 3.9+)
- Odoo model methods don't require type hints (Odoo ORM complexity)

### Testing

- All pure helper functions must have unit tests
- Tests go in `tests/` directory
- Test file naming: `test_*.py`
- Test class naming: `Test*`
- Test function naming: `test_*`
- Use descriptive test names that explain what is being tested

### Documentation

- All functions must have docstrings
- Use Google-style docstrings with Args, Returns, Raises sections
- Keep docstrings concise but informative

## Git Hooks

The project includes a pre-push git hook that automatically runs checks before pushing:

```bash
./scripts/install-git-hooks.sh
```

The hook will:
- Run linting (ruff)
- Run tests (pytest)
- Run type checking (mypy, if available)
- Prevent push if any check fails

To skip the hook (not recommended): `git push --no-verify`

## Pre-Commit Checklist

Before committing code:

1. Run `make check` or `./scripts/pre_deploy_check.sh`
2. Ensure all tests pass
3. Verify no sensitive data is committed
4. Check that error messages are user-friendly
5. Ensure logging is consistent

Note: If you've installed git hooks, checks will run automatically on push.

## Git Workflow

1. Make changes on a feature branch
2. Run pre-deployment checks locally
3. Commit with clear, descriptive messages
4. Push to GitHub
5. Create pull request (if not working directly on main)
6. After merge to main, GitHub Actions will automatically deploy

## Deployment

- Only deploy from `main` branch
- All checks must pass before deployment
- Use atomic `git pull --ff-only` for deployments
- Never skip pre-deployment checks
