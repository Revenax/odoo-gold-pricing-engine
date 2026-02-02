# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import re
from decimal import ROUND_HALF_UP, Decimal


def get_markup_per_gram(env, gold_type: str) -> float:
    """
    Read markup per gram from system parameters.

    Args:
        env: Odoo environment
        gold_type: Gold type key (e.g. jewellery_local, bars)

    Returns:
        float: Markup per gram, 0.0 if not configured or invalid
    """
    if not gold_type:
        return 0.0

    param_key = f'gold_pricing.markup_{gold_type}'
    raw_value = env['ir.config_parameter'].sudo().get_param(param_key, '0.0')
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return 0.0


def parse_gold_price_from_text(text: str) -> float:
    """
    Parse gold price from Arabic text response.

    Expected format: "علما بأن سعر البيع لجرام الذهب عيار 21 هو 5415 جنيها"
    Extracts number after "الذهب عيار 21 هو "

    Args:
        text: HTML/text response containing Arabic text with gold price

    Returns:
        float: Extracted 21K gold price per gram

    Raises:
        ValueError: If price cannot be extracted or is invalid
    """
    # Primary pattern: extract number after "الذهب عيار 21 هو "
    match = re.search(r'(?<=الذهب عيار 21 هو )\d+', text)

    if match:
        price = int(match.group(0))
        if price <= 0:
            raise ValueError(f'Invalid price extracted: {price}')
        return float(price)

    # Fallback: try to find any large number that might be a price
    numbers = re.findall(r'\d+', text)
    if numbers:
        # Use the largest number found (likely the price)
        potential_prices = [int(n) for n in numbers if len(n) >= 3]
        if potential_prices:
            potential_price = max(potential_prices)
            if potential_price > 0:
                return float(potential_price)

    raise ValueError('Price not found in API response')


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
            - sale_price: Sale price (cost + markup_total)
            - min_sale_price: Minimum sale price (cost + markup_total × 0.5)
    """
    # Purity factors mapping (relative to 21K, which is what the API returns)
    purity_factors = {
        '24K': Decimal('0.999') / Decimal('0.875'),  # 1.1417
        '21K': Decimal('1.0'),                       # 1.0000
        '18K': Decimal('0.750') / Decimal('0.875'),  # 0.8571
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
        raise ValueError(f'Base gold price must be greater than 0, got: {base_gold_price_21k}')
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

    # Calculate minimum sale price: cost + (markup_total × 0.5)
    min_sale_price = (cost + (markup_total * Decimal('0.5'))).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    return (float(cost), float(sale_price), float(min_sale_price))
