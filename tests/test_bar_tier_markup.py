# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

"""Unit tests for bars weight-tier markup (closest-neighbor resolution)."""

import os
import sys

try:
    from gold_pricing_utils import _get_markup_bars_by_weight
except ImportError:
    import importlib.util
    _project_root = os.path.join(os.path.dirname(__file__), '..')
    sys.path.insert(0, os.path.abspath(_project_root))
    _utils_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..",
                     "gold_pricing", "utils.py")
    )
    spec = importlib.util.spec_from_file_location("utils", _utils_path)
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)
    _get_markup_bars_by_weight = utils._get_markup_bars_by_weight


def _make_env(params=None):
    defaults = {
        'gold_pricing.markup_bars_1g': '200',
        'gold_pricing.markup_bars_2_5g': '200',
        'gold_pricing.markup_bars_5g': '125',
        'gold_pricing.markup_bars_10g': '120',
        'gold_pricing.markup_bars_20g': '120',
        'gold_pricing.markup_bars_31g': '115',
        'gold_pricing.markup_bars_50g': '100',
        'gold_pricing.markup_bars_100g': '100',
        'gold_pricing.markup_bars_250g': '80',
        'gold_pricing.markup_bars_500g': '80',
        'gold_pricing.markup_bars_1000g': '80',
    }
    if params:
        defaults.update(params)
    stored = defaults

    class ICP:
        def get_param(self, key, default='0.0'):
            return stored.get(key, default)

    class Env:
        def __getitem__(self, k):
            if k == 'ir.config_parameter':
                return type('ICP', (), {'sudo': lambda self: ICP()})()
            raise KeyError(k)

    return Env()


def test_bars_3g_uses_2_5g_tier():
    """3g is closest to 2.5g tier -> 200 EGP/g."""
    env = _make_env()
    assert _get_markup_bars_by_weight(env, 3.0) == 200.0


def test_bars_7_5g_tie_uses_lower_tier_5g():
    """7.5g ties 5 and 10; use lower (5g) -> 125 EGP/g."""
    env = _make_env()
    assert _get_markup_bars_by_weight(env, 7.5) == 125.0


def test_bars_1000g_plus_uses_1000g_tier():
    """Weight >= 1000 uses 1000g+ tier -> 80 EGP/g."""
    env = _make_env()
    assert _get_markup_bars_by_weight(env, 1000.0) == 80.0
    assert _get_markup_bars_by_weight(env, 1500.0) == 80.0


def test_bars_exact_tier():
    """Exact weight returns that tier's markup."""
    env = _make_env()
    assert _get_markup_bars_by_weight(env, 1.0) == 200.0
    assert _get_markup_bars_by_weight(env, 31.0) == 115.0


def test_bars_zero_weight_returns_zero():
    """Zero or negative weight returns 0."""
    env = _make_env()
    assert _get_markup_bars_by_weight(env, 0.0) == 0.0
    assert _get_markup_bars_by_weight(env, -1.0) == 0.0


if __name__ == '__main__':
    test_bars_3g_uses_2_5g_tier()
    test_bars_7_5g_tie_uses_lower_tier_5g()
    test_bars_1000g_plus_uses_1000g_tier()
    test_bars_exact_tier()
    test_bars_zero_weight_returns_zero()
    print('All bar tier markup tests passed.')
