# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import re
from decimal import ROUND_HALF_UP, Decimal

# Bar markup tiers: (weight_g, config_param_suffix). Weight 1000 means 1000g+.
BAR_TIER_WEIGHTS = [1, 2.5, 5, 10, 20, 31, 50, 100, 250, 500, 1000]
BAR_TIER_PARAM_SUFFIXES = [
    '1g', '2_5g', '5g', '10g', '20g', '31g', '50g', '100g', '250g', '500g', '1000g',
]


def _get_markup_bars_by_weight(env, weight_g: float) -> float:
    """
    Resolve bars markup per gram from weight using tier table (closest neighbor).
    Weights >= 1000 use the 1000g tier. Tie-break: use lower weight tier.
    """
    if weight_g <= 0:
        return 0.0
    ICP = env['ir.config_parameter'].sudo()
    if weight_g >= 1000:
        raw = ICP.get_param('gold_pricing.markup_bars_1000g', '0.0')
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0
    # Closest tier by distance; tie -> lower weight
    best_weight = BAR_TIER_WEIGHTS[0]
    best_dist = abs(weight_g - best_weight)
    for w in BAR_TIER_WEIGHTS:
        if w >= 1000:
            continue
        d = abs(weight_g - w)
        if d < best_dist:
            best_dist = d
            best_weight = w
    idx = BAR_TIER_WEIGHTS.index(best_weight)
    param_key = f'gold_pricing.markup_bars_{BAR_TIER_PARAM_SUFFIXES[idx]}'
    raw_value = ICP.get_param(param_key, '0.0')
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return 0.0


def get_markup_per_gram(env, gold_type: str, weight_g=None) -> float:
    """
    Read markup per gram from system parameters.

    For jewellery_local / jewellery_foreign, weight_g is ignored.
    For bars, weight_g is required; markup is resolved by weight tier (closest neighbor).

    Args:
        env: Odoo environment
        gold_type: Gold type key (jewellery_local, jewellery_foreign, bars)
        weight_g: Required when gold_type is 'bars'; used for tier lookup

    Returns:
        float: Markup per gram, 0.0 if not configured or invalid
    """
    if not gold_type:
        return 0.0

    if gold_type == 'bars':
        if weight_g is None or weight_g <= 0:
            return 0.0
        return _get_markup_bars_by_weight(env, weight_g)

    param_key = f'gold_pricing.markup_{gold_type}'
    raw_value = env['ir.config_parameter'].sudo().get_param(param_key, '0.0')
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return 0.0


def parse_gold_price_with_regex(text: str, pattern: str) -> float:
    """
    Extract 21K gold price from text using a configurable regex pattern.

    The pattern is applied to the text. If it has a capturing group, the first
    group is used as the price string; otherwise the full match is used. The
    result is parsed as a float (supports integers and decimals).

    Args:
        text: HTML or plain text response (e.g. from Gold API endpoint).
        pattern: Regular expression that matches the price. Prefer one capturing
            group containing the number (e.g. r'(\\d+(?:\\.\\d+)?)').

    Returns:
        float: Extracted 21K gold price per gram.

    Raises:
        ValueError: If pattern is invalid, no match, or parsed value is not a
            valid positive number.
    """
    if not pattern or not pattern.strip():
        raise ValueError('Gold 21K regex formula is empty.')

    try:
        compiled = re.compile(pattern)
    except re.error as e:
        raise ValueError(f'Invalid Gold 21K regex formula: {e}') from e

    match = compiled.search(text)
    if not match:
        raise ValueError(
            'Price not found in API response (regex did not match).')

    if match.groups():
        extracted = match.group(1).strip()
    else:
        extracted = match.group(0).strip()

    if not extracted:
        raise ValueError('Price not found in API response (empty match).')

    # Allow digits and one decimal point; strip other characters for localization
    normalized = re.sub(r'[^\d.]', '', extracted)
    if not normalized:
        raise ValueError(
            f'Extracted value is not a valid number: {extracted!r}')

    try:
        price = float(normalized)
    except ValueError as e:
        raise ValueError(
            f'Extracted value is not a valid number: {extracted!r}') from e

    if price <= 0:
        raise ValueError(
            f'Invalid price extracted: {price} (must be greater than 0).')

    return price


def compute_gold_product_price(
    base_gold_price_21k: float,
    purity: str,
    weight_g: float,
    markup_per_gram: float,
) -> tuple[float, float, float]:
    """
    Compute gold product prices from base price, purity, weight, and markup.

    Args:
        base_gold_price_21k: Base 21K gold price per gram (from API)
        purity: Gold purity ('24K', '21K', '18K', '14K', '10K')
        weight_g: Weight of gold in grams
        markup_per_gram: Markup per gram (from settings)

    Returns:
        tuple: (cost_price, sale_price, min_sale_price)
            - cost_price: Cost price (base × purity_factor × weight)
            - sale_price: Sale price (cost + markup), rounded to nearest 50
            - min_sale_price: Minimum sale price (cost + 70% markup), rounded to nearest 50
    """
    # Purity factors mapping (relative to 21K, which is what the API returns)
    # 24K = 8/7 of 21K; 18K = 7/8 of 21K
    purity_factors = {
        '24K': Decimal('8') / Decimal('7'),         # 8/7 of 21K
        '21K': Decimal('1.0'),                       # 1.0000
        '18K': Decimal('7') / Decimal('8'),          # 7/8 of 21K
        '14K': Decimal('0.583') / Decimal('0.875'),  # 0.6663
        '10K': Decimal('0.417') / Decimal('0.875'),  # 0.4766
    }

    purity_factor = purity_factors.get(purity, Decimal('0'))
    if purity_factor <= 0:
        raise ValueError(f'Invalid purity: {purity}')

    # Validate inputs
    if weight_g <= 0:
        raise ValueError(f'Weight must be greater than 0, got: {weight_g}')
    if base_gold_price_21k <= 0:
        raise ValueError(
            f'Base gold price must be greater than 0, got: {base_gold_price_21k}')
    if markup_per_gram < 0:
        raise ValueError(f'Markup cannot be negative, got: {markup_per_gram}')

    # Use Decimal for precise calculations
    weight = Decimal(str(weight_g))
    base_price = Decimal(str(base_gold_price_21k))
    markup = Decimal(str(markup_per_gram))

    # Calculate cost: (21K price from API) × purity_factor × weight
    adjusted_gold_price = base_price * purity_factor
    cost = (adjusted_gold_price * weight).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    # Calculate markup total: markup × weight
    markup_total = (markup * weight).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    # Calculate sale price: cost + markup_total
    sale_price = (cost + markup_total).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    # Calculate minimum sale price: cost + (markup_total × 0.7)
    min_sale_price = (cost + (markup_total * Decimal('0.7'))).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    # Round both to nearest 50 (min_sale first, then sale)
    round_to_50 = Decimal('50')
    min_sale_price = (min_sale_price / round_to_50).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP
    ) * round_to_50
    sale_price = (sale_price / round_to_50).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP
    ) * round_to_50

    return (float(cost), float(sale_price), float(min_sale_price))
