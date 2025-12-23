# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import logging
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GoldPriceService(models.Model):
    _name = 'gold.price.service'
    _description = 'Gold Price Service'
    
    # Cache for current gold price
    _current_gold_price = None
    _price_cache_time = None
    
    def get_current_gold_price(self):
        """
        Get current gold price from API or cache.
        Returns price per gram in base currency.
        
        :return: float - Gold price per gram
        """
        # In production, implement proper caching with expiration
        # For now, fetch from API each time (cron will update frequently)
        try:
            return self._fetch_gold_price_from_api()
        except Exception as e:
            _logger.error('Failed to fetch gold price from API: %s', str(e))
            # Fallback to last known price from config or default
            return self._get_fallback_price()
    
    def _fetch_gold_price_from_api(self):
        """
        Fetch gold price from external API.
        Replace URL with actual API endpoint.
        
        Expected API response format (JSON):
        {
            "price_per_gram": 75.50,
            "currency": "USD",
            "timestamp": "2026-01-01T12:00:00Z"
        }
        
        :return: float - Gold price per gram
        """
        api_url = self.env['ir.config_parameter'].sudo().get_param(
            'gold_pricing.api_url',
            'https://api.example.com/gold/price'
        )
        
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'gold_pricing.api_key',
            ''
        )
        
        timeout = 10
        headers = {}
        
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        try:
            response = requests.get(api_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            
            # Extract price from response
            # Adjust these keys based on your actual API response structure
            price_per_gram = data.get('price_per_gram') or data.get('price') or data.get('rate')
            
            if not price_per_gram:
                raise ValueError('Price not found in API response')
            
            return float(price_per_gram)
            
        except requests.exceptions.RequestException as e:
            _logger.error('API request failed: %s', str(e))
            raise
        except (ValueError, KeyError) as e:
            _logger.error('Invalid API response format: %s', str(e))
            raise
    
    def _get_fallback_price(self):
        """
        Get fallback gold price from system parameters.
        Used when API is unavailable.
        
        :return: float - Fallback gold price per gram
        """
        fallback_price = self.env['ir.config_parameter'].sudo().get_param(
            'gold_pricing.fallback_price',
            '75.0'  # Default fallback price
        )
        return float(fallback_price)
    
    def update_all_gold_product_prices(self):
        """
        Update prices for all gold products.
        Called by cron job every 10 minutes.
        
        :return: dict - Execution summary
        """
        _logger.info('Starting gold price update for all products')
        
        try:
            # Fetch current gold price
            base_gold_price = self._fetch_gold_price_from_api()
            _logger.info('Fetched gold price: %s per gram', base_gold_price)
            
            # Get all gold products
            gold_products = self.env['product.template'].search([
                ('is_gold_product', '=', True),
                ('gold_purity', '!=', False),
            ])
            
            if not gold_products:
                _logger.info('No gold products found to update')
                return {
                    'success': True,
                    'products_updated': 0,
                    'base_price': base_gold_price,
                    'message': 'No gold products found',
                }
            
            # Update prices in batches for performance
            batch_size = 100
            total_updated = 0
            
            for i in range(0, len(gold_products), batch_size):
                batch = gold_products[i:i + batch_size]
                batch.update_gold_prices(base_gold_price)
                total_updated += len(batch)
                _logger.info('Updated batch: %d products (total: %d)', len(batch), total_updated)
            
            _logger.info(
                'Gold price update completed: %d products updated with base price %s',
                total_updated,
                base_gold_price
            )
            
            return {
                'success': True,
                'products_updated': total_updated,
                'base_price': base_gold_price,
                'message': f'Successfully updated {total_updated} products',
            }
            
        except Exception as e:
            _logger.error('Gold price update failed: %s', str(e), exc_info=True)
            return {
                'success': False,
                'products_updated': 0,
                'base_price': None,
                'message': f'Update failed: {str(e)}',
                'error': str(e),
            }

