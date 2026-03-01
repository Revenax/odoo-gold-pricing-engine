# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import logging

from odoo import api, models

from ..utils import compute_silver_product_price  # noqa: E402

_logger = logging.getLogger(__name__)


class SilverPriceService(models.Model):
    _name = 'silver.price.service'
    _description = 'Silver Price Service'

    @api.model
    def get_current_silver_price_999(self):
        """
        Get current silver 999 price per gram from stored param.
        Value is set by the Selenium script (scripts/selenium_automation.py)
        which renders the page and reads the XPath element.
        """
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'jewellery_evaluator.silver_fallback_price', '0.0'
        )
        try:
            val = float(str(raw).replace(',', '').strip())
            return val if val >= 0 else 0.0
        except (ValueError, TypeError):
            return 0.0

    @api.model
    def set_silver_price_999(self, price_per_gram):
        """Store silver 999 price. Called by Selenium script via RPC."""
        if price_per_gram is None or price_per_gram <= 0:
            return
        self.env['ir.config_parameter'].sudo().set_param(
            'jewellery_evaluator.silver_fallback_price', str(price_per_gram)
        )
        _logger.info('Silver 999 price updated: %s per gram', price_per_gram)

    @api.model
    def update_all_silver_product_prices(self):
        """
        Update prices for all silver products.
        Called by cron every 10 minutes and after Settings are saved.
        Uses stored price (set by Selenium script or manually in Settings).
        """
        _logger.info('Starting silver price update for all products')
        try:
            base_silver = self.get_current_silver_price_999()
            if base_silver <= 0:
                _logger.warning(
                    'Silver price not set. Run scripts/selenium_automation.py with ODOO_* env vars.')
                return {
                    'success': True, 'products_updated': 0,
                    'base_price': 0.0, 'message': 'Silver price not configured',
                }
            _logger.info('Silver price: %s per gram', base_silver)

            silver_products = self.env['product.template'].search([
                ('jewellery_type', '=', 'silver'),
                ('silver_purity', '!=', False),
                ('jewellery_weight_g', '>', 0),
            ])

            if not silver_products:
                _logger.info('No silver products found to update')
                return {
                    'success': True, 'products_updated': 0,
                    'base_price': base_silver, 'message': 'No silver products found',
                }

            silver_products.update_silver_prices(base_silver)
            total = len(silver_products)
            _logger.info(
                'Silver price update completed: %d products, base %s', total, base_silver)
            return {
                'success': True, 'products_updated': total,
                'base_price': base_silver, 'message': f'Updated {total} products',
            }
        except Exception as e:
            _logger.error('Silver price update failed: %s',
                          str(e), exc_info=True)
            return {
                'success': False, 'products_updated': 0,
                'base_price': None, 'message': str(e), 'error': str(e),
            }
