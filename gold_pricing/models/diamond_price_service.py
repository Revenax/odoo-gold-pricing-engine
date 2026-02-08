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

        Returns:
            float: Diamond price in USD
        """
        return 50.0

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
            'gold_pricing.global_diamond_discount', '80'
        )
        try:
            value = int(raw)
            return max(0, min(80, value))
        except (TypeError, ValueError):
            return 80

    def update_all_diamond_product_prices(self):
        """
        Update prices for all diamond products using the latest USD price.

        :return: dict - Execution summary
        """
        price_usd = self.get_current_diamond_price_usd()
        exchange_rate = self.get_usd_to_egp_rate()
        discount_pct = self.get_global_diamond_discount()
        price_egp = (price_usd * exchange_rate) * (100 - discount_pct) / 100.0

        diamond_products = self.env['product.template'].search([
            ('is_diamond_product', '=', True),
        ])

        if not diamond_products:
            return {
                'success': True,
                'products_updated': 0,
                'price_usd': price_usd,
                'message': 'No diamond products found',
            }

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
