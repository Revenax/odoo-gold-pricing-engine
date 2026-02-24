# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import os
import sys

try:
    from jewellery_evaluator_utils import parse_gold_price_with_regex  # noqa: F401
except ImportError:
    import importlib.util

    _project_root = os.path.join(os.path.dirname(__file__), '..')
    sys.path.insert(0, os.path.abspath(_project_root))

    _utils_path = os.path.join(os.path.dirname(
        __file__), "..", "jewellery_evaluator", "utils.py")
    _utils_path = os.path.abspath(_utils_path)

    if not os.path.exists(_utils_path):
        raise FileNotFoundError(
            f"utils.py not found at {_utils_path}") from None

    spec = importlib.util.spec_from_file_location("utils", _utils_path)
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)
    parse_gold_price_with_regex = utils.parse_gold_price_with_regex


def test_extract_price_with_capturing_group():
    """Extracted value is the first capturing group."""
    text = "علما بأن سعر البيع لجرام الذهب عيار 21 هو 5415 جنيها"
    pattern = r"الذهب عيار 21 هو (\d+)"
    assert parse_gold_price_with_regex(text, pattern) == 5415.0


def test_extract_price_full_match():
    """When pattern has no group, full match is used."""
    text = "Gold price is 5000 EGP per gram"
    pattern = r"\d+"
    assert parse_gold_price_with_regex(text, pattern) == 5000.0


def test_extract_decimal_price():
    """Decimal price is parsed correctly."""
    text = "<span>21K: 1234.56</span>"
    pattern = r"21K:\s*(\d+(?:\.\d+)?)"
    assert parse_gold_price_with_regex(text, pattern) == 1234.56


def test_no_match_raises_error():
    """ValueError when regex does not match."""
    try:
        parse_gold_price_with_regex("No price information available", r"(\d+)")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "Price not found" in str(e) or "did not match" in str(e)


def test_empty_text_no_match_raises_error():
    """ValueError when text is empty and pattern does not match."""
    try:
        parse_gold_price_with_regex("", r"(\d+)")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "Price not found" in str(e) or "did not match" in str(e)


def test_invalid_regex_raises_error():
    """ValueError when pattern is invalid."""
    try:
        parse_gold_price_with_regex("price 100", r"[unclosed")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "Invalid" in str(e) or "regex" in str(e).lower()


def test_empty_pattern_raises_error():
    """ValueError when pattern is empty."""
    try:
        parse_gold_price_with_regex("price 100", "")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "empty" in str(e).lower()
