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
sys.path.insert(0, os.path.abspath(_project_root))

# Load utils module directly
_utils_path = os.path.join(os.path.dirname(__file__), "..", "gold_pricing", "utils.py")
_utils_path = os.path.abspath(_utils_path)

if os.path.exists(_utils_path):
    spec = importlib.util.spec_from_file_location("gold_pricing_utils", _utils_path)
    utils_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils_module)

    # Make utils available to all tests
    sys.modules['gold_pricing_utils'] = utils_module
