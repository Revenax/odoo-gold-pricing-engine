# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import logging

from odoo import models

from ..utils import compute_silver_product_price  # noqa: E402

_logger = logging.getLogger(__name__)


class SilverPriceService(models.Model):
    _name = 'silver.price.service'
    _description = 'Silver Price Service'

    def get_current_silver_price_999(self):
        """
        Get current silver 999 price per gram from system parameters.

        The value can be set manually in Settings or by an external job (e.g.
        script that scrapes dahabmasr.com and updates via RPC). Use the
        Selenium script in scripts/selenium_automation.py and feed its
        output into this parameter.

        :return: float - Silver 999 price per gram (EGP)
        """
        try:
            return self._get_stored_silver_price()
        except Exception as e:
            _logger.error('Failed to get silver price: %s', str(e))
            return self._get_fallback_silver_price()

    def _get_stored_silver_price(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'jewellery_evaluator.silver_999_price', ''
        )
        if not raw or not str(raw).strip():
            return self._get_fallback_silver_price()
        return self._parse_silver_price_string(raw) or self._get_fallback_silver_price()

    def _parse_silver_price_string(self, raw):
        """Parse a price string that may contain 'EGP' or commas (e.g. '165EGP', '1,234.56')."""
        if raw is None:
            return None
        s = str(raw).strip().replace(',', '')
        # Strip trailing non-numeric (e.g. EGP)
        s = s.rstrip('EGPegp \t').strip()
        if not s:
            return None
        try:
            value = float(s)
            return value if value > 0 else None
        except (ValueError, TypeError):
            return None

    def _get_fallback_silver_price(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'jewellery_evaluator.silver_fallback_price', '0.0'
        )
        try:
            value = float(str(raw).replace(',', '').strip())
            return value if value >= 0 else 0.0
        except (ValueError, TypeError):
            return 0.0

    def set_silver_price_999(self, price_per_gram):
        """
        Store silver 999 price per gram (e.g. from Selenium script or API).

        Call from external script via XML-RPC/JSON-RPC or from Settings.

        :param price_per_gram: float - Silver 999 price per gram (EGP)
        """
        if price_per_gram is None or price_per_gram <= 0:
            return
        self.env['ir.config_parameter'].sudo().set_param(
            'jewellery_evaluator.silver_999_price',
            str(price_per_gram),
        )
        _logger.info('Silver 999 price updated: %s per gram', price_per_gram)

    def update_all_silver_product_prices(self):
        """
        Update list prices for all silver products using stored silver 999 price.

        Called by cron every 10 minutes (same as gold).
        """
        _logger.info('Starting silver price update for all products')
        try:
            base_silver = self.get_current_silver_price_999()
            if base_silver <= 0:
                _logger.warning(
                    'Silver 999 price not set or zero. Set '
                    'jewellery_evaluator.silver_999_price or silver_fallback_price.'
                )
                return {
                    'success': True,
                    'products_updated': 0,
                    'base_price': 0.0,
                    'message': 'Silver price not configured',
                }

            _logger.info('Silver 999 price: %s per gram', base_silver)

            silver_products = self.env['product.template'].search([
                ('jewellery_type', '=', 'silver'),
                ('silver_purity', '!=', False),
                ('jewellery_weight_g', '>', 0),
            ])

            if not silver_products:
                _logger.info('No silver products found to update')
                return {
                    'success': True,
                    'products_updated': 0,
                    'base_price': base_silver,
                    'message': 'No silver products found',
                }

            silver_products.update_silver_prices(base_silver)
            total = len(silver_products)
            _logger.info(
                'Silver price update completed: %d products, base %s',
                total, base_silver,
            )
            return {
                'success': True,
                'products_updated': total,
                'base_price': base_silver,
                'message': f'Successfully updated {total} products',
            }
        except Exception as e:
            _logger.error('Silver price update failed: %s', str(e), exc_info=True)
            return {
                'success': False,
                'products_updated': 0,
                'base_price': None,
                'message': str(e),
                'error': str(e),
            }
