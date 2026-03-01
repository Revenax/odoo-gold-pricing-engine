# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import logging

import requests
from odoo import models

from ..utils import compute_silver_product_price, parse_gold_price_with_regex  # noqa: E402

_logger = logging.getLogger(__name__)


class SilverPriceService(models.Model):
    _name = 'silver.price.service'
    _description = 'Silver Price Service'

    def get_current_silver_price_999(self):
        """
        Get current silver 999 price per gram from API or fallback.
        Returns silver 999 price per gram (EGP).
        """
        try:
            return self._fetch_silver_price_from_api()
        except Exception as e:
            _logger.error('Failed to fetch silver price from API: %s', str(e))
            return self._get_fallback_price()

    def _fetch_silver_price_from_api(self):
        """
        Fetch silver 999 price from external API via GET request.
        On HTTP 200, extracts the price using the configurable regex.
        Updates fallback on success.
        """
        api_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'jewellery_evaluator.silver_api_endpoint', ''
        )
        regex_formula = self.env['ir.config_parameter'].sudo().get_param(
            'jewellery_evaluator.silver_999_regex_formula', ''
        )

        if not api_endpoint or not api_endpoint.strip():
            raise ValueError(
                'Silver API endpoint is not configured. Set jewellery_evaluator.silver_api_endpoint'
            )
        if not regex_formula or not regex_formula.strip():
            raise ValueError(
                'Silver 999 regex formula is not configured. Set jewellery_evaluator.silver_999_regex_formula'
            )

        has_http = api_endpoint.startswith('http://') or api_endpoint.startswith('https://')
        if not has_http:
            raise ValueError('Silver API endpoint must be a valid HTTP/HTTPS URL.')

        timeout = 10
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }

        try:
            response = requests.get(api_endpoint, headers=headers, timeout=timeout)
            response.raise_for_status()
            price = parse_gold_price_with_regex(response.text, regex_formula)
            self.env['ir.config_parameter'].sudo().set_param(
                'jewellery_evaluator.silver_fallback_price', str(price)
            )
            _logger.info('Silver price fetched: %s; fallback updated', price)
            return price
        except requests.exceptions.Timeout:
            raise ValueError('Silver API request timed out.') from None
        except requests.exceptions.ConnectionError:
            raise ValueError('Failed to connect to silver API.') from None
        except requests.exceptions.HTTPError as e:
            raise ValueError(f'Silver API returned HTTP {e.response.status_code}') from e
        except requests.exceptions.RequestException:
            raise ValueError('Silver API request failed.') from None
        except ValueError:
            raise

    def _get_fallback_price(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'jewellery_evaluator.silver_fallback_price', '0.0'
        )
        try:
            val = float(str(raw).replace(',', '').strip())
            return val if val >= 0 else 0.0
        except (ValueError, TypeError):
            return 0.0

    def update_all_silver_product_prices(self):
        """
        Update prices for all silver products.
        Called by cron every 10 minutes.
        Uses get_current (fetch or fallback) so products update even when API fails.
        """
        _logger.info('Starting silver price update for all products')
        try:
            base_silver = self.get_current_silver_price_999()
            if base_silver <= 0:
                _logger.warning('Silver price not configured (API and fallback).')
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
            _logger.info('Silver price update completed: %d products, base %s', total, base_silver)
            return {
                'success': True, 'products_updated': total,
                'base_price': base_silver, 'message': f'Updated {total} products',
            }
        except Exception as e:
            _logger.error('Silver price update failed: %s', str(e), exc_info=True)
            return {
                'success': False, 'products_updated': 0,
                'base_price': None, 'message': str(e), 'error': str(e),
            }
