# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import models


class DiamondPriceService(models.Model):
    _name = 'diamond.price.service'
    _description = 'Diamond Price Service'

    def get_current_diamond_price_usd(self):
        """
        Placeholder for diamond price API.
        Override to fetch real data. Return None when no API data is available.

        Returns:
            float|None: Diamond price in USD, or None if no global source (keep per-product prices)
        """
        return None

    def _has_global_diamond_price_api(self):
        """True if a global diamond price is used (cron may overwrite product diamond_usd_price)."""
        return self.get_current_diamond_price_usd() is not None

    def get_usd_to_egp_rate(self):
        """
        Placeholder for USD to EGP exchange rate.

        Returns:
            float: USD to EGP exchange rate
        """
        return 50.0

    def get_global_diamond_discount(self):
        """
        Return global diamond discount percentage (0-80) from settings.
        Sale price = (USD * USD/EGP rate) * (100 - discount) / 100.

        Returns:
            int: Discount percentage in range 0-80 (default 80)
        """
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'jewellery_evaluator.global_diamond_discount', '80'
        )
        try:
            value = int(raw)
            return max(0, min(80, value))
        except (TypeError, ValueError):
            return 80

    def update_all_diamond_product_prices(self):
        """
        Update prices for all diamond products.
        When a global diamond price API is available, overwrites diamond_usd_price and list_price.
        When not (placeholder), only refreshes list_price from each product's diamond_usd_price.

        :return: dict - Execution summary
        """
        price_usd = self.get_current_diamond_price_usd()
        exchange_rate = self.get_usd_to_egp_rate()
        discount_pct = self.get_global_diamond_discount()

        diamond_products = self.env['product.template'].search([
            ('jewellery_type', '=', 'diamond_jewellery'),
        ])

        if not diamond_products:
            return {
                'success': True,
                'products_updated': 0,
                'price_usd': price_usd,
                'message': 'No diamond products found',
            }

        if self._has_global_diamond_price_api():
            price_egp = (price_usd * exchange_rate) * \
                (100 - discount_pct) / 100.0
            for product in diamond_products:
                product.with_context(skip_diamond_price_update=True).write({
                    'diamond_usd_price': price_usd,
                    'list_price': price_egp,
                })
            return {
                'success': True,
                'products_updated': len(diamond_products),
                'price_usd': price_usd,
                'price_egp': price_egp,
                'exchange_rate': exchange_rate,
                'message': f'Successfully updated {len(diamond_products)} products',
            }

        for product in diamond_products:
            if product.diamond_usd_price and product.diamond_usd_price > 0:
                price_egp = (product.diamond_usd_price * exchange_rate) * (
                    100 - discount_pct
                ) / 100.0
                product.with_context(skip_diamond_price_update=True).write({
                    'list_price': price_egp,
                })

        return {
            'success': True,
            'products_updated': len(diamond_products),
            'price_usd': None,
            'exchange_rate': exchange_rate,
            'message': f'Refreshed list_price for {len(diamond_products)} products (no global price API)',
        }
