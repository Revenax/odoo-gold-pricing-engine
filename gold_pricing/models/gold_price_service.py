# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import logging
import re
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
        Fetch gold price from external API using cookie authentication.
        Parses Arabic text response to extract 21K gold price.
        
        Expected API response format (HTML/text with Arabic):
        "علما بأن سعر البيع لجرام الذهب عيار 21 هو 5415 جنيها"
        Extracts price after "الذهب عيار 21 هو "
        
        :return: float - Gold price per gram (21K price)
        """
        api_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'gold_api_endpoint',
            ''
        )
        
        api_cookie = self.env['ir.config_parameter'].sudo().get_param(
            'gold_api_cookie',
            ''
        )
        
        if not api_endpoint:
            raise ValueError('GOLD_API_ENDPOINT is not configured. Please set gold_api_endpoint system parameter.')
        
        if not api_cookie:
            raise ValueError('GOLD_API_COOKIE is not configured. Please set gold_api_cookie system parameter.')
        
        timeout = 10
        headers = {
            'Cookie': api_cookie,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.7',
            'cache-control': 'max-age=0',
            'dnt': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="142", "Brave";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
        }
        
        try:
            response = requests.get(api_endpoint, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Parse as text/HTML (for Arabic text APIs)
            text = response.text
            
            # Parse Arabic text to extract 21K gold price
            # Pattern: "علما بأن سعر البيع لجرام الذهب عيار 21 هو 5415 جنيها"
            # Extract number after "الذهب عيار 21 هو "
            match = re.search(r'(?<=الذهب عيار 21 هو )\d+', text)
            
            if match:
                price = int(match.group(0))
                if price <= 0:
                    raise ValueError(f'Invalid price extracted: {price}')
                # Return price as float (assuming price is per gram)
                return float(price)
            
            # If no Arabic pattern found, try alternative patterns
            # Try to find any number that might be a price
            numbers = re.findall(r'\d+', text)
            if numbers:
                # Use the largest number found (likely the price)
                potential_price = max([int(n) for n in numbers if len(n) >= 3])
                if potential_price > 0:
                    _logger.warning('Extracted price using fallback pattern: %s', potential_price)
                    return float(potential_price)
            
            raise ValueError('Price not found in API response')
            
        except requests.exceptions.RequestException as e:
            _logger.error('API request failed: %s', str(e))
            raise
        except (ValueError, KeyError, AttributeError) as e:
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

