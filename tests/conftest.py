# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

"""
Pytest configuration - ensures utils module is available for tests.
"""

import importlib.util
import os
import sys

# Add project root to path
_project_root = os.path.join(os.path.dirname(__file__), '..')
_project_root = os.path.abspath(_project_root)
sys.path.insert(0, _project_root)


def pytest_ignore_collect(collection_path, config):
    """Do not collect repo root __init__.py (repo dir name may have hyphens; not a valid package)."""
    try:
        root = config.rootpath.resolve()
        path = collection_path.resolve()
        if path.name == "__init__.py" and path.parent == root:
            return True
    except Exception:
        pass
    return False

# Load utils module directly
_utils_path = os.path.join(os.path.dirname(__file__), "..", "jewellery_evaluator", "utils.py")
_utils_path = os.path.abspath(_utils_path)

if os.path.exists(_utils_path):
    spec = importlib.util.spec_from_file_location("jewellery_evaluator_utils", _utils_path)
    utils_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_module)

    # Make utils available to all tests
    sys.modules['jewellery_evaluator_utils'] = utils_module
