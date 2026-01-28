# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import os
import sys

# Import utils from conftest-loaded module or load directly
try:
    from gold_pricing_utils import parse_gold_price_from_text  # noqa: F401
except ImportError:
    # Fallback: load directly
    import importlib.util

    _project_root = os.path.join(os.path.dirname(__file__), '..')
    sys.path.insert(0, os.path.abspath(_project_root))

    _utils_path = os.path.join(os.path.dirname(__file__), "..", "gold_pricing", "utils.py")
    _utils_path = os.path.abspath(_utils_path)

    if not os.path.exists(_utils_path):
        raise FileNotFoundError(f"utils.py not found at {_utils_path}") from None

    spec = importlib.util.spec_from_file_location("utils", _utils_path)
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)
    parse_gold_price_from_text = utils.parse_gold_price_from_text


def test_extract_price_from_arabic_text():
    """Test extraction of price from expected Arabic format."""
    text = "علما بأن سعر البيع لجرام الذهب عيار 21 هو 5415 جنيها"
    assert parse_gold_price_from_text(text) == 5415.0


def test_fallback_pattern_extraction():
    """Test fallback pattern when Arabic pattern not found."""
    text = "Gold price is 5000 EGP per gram"
    assert parse_gold_price_from_text(text) == 5000.0


def test_no_price_found_raises_error():
    """Test that ValueError is raised when no price found."""
    try:
        parse_gold_price_from_text("No price information available")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "Price not found" in str(e)


def test_empty_text_raises_error():
    """Test that empty text raises ValueError."""
    try:
        parse_gold_price_from_text("")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass
