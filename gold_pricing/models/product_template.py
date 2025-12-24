# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Gold-specific fields
    gold_weight_g = fields.Float(
        string='Gold Weight (grams)',
        digits=(16, 4),
        help='Weight of gold in grams. Required for gold products.',
    )
    
    gold_purity = fields.Selection(
        selection=[
            ('24K', '24K (99.9% pure)'),
            ('21K', '21K (87.5% pure)'),
            ('18K', '18K (75.0% pure)'),
            ('14K', '14K (58.3% pure)'),
            ('10K', '10K (41.7% pure)'),
        ],
        string='Gold Purity',
        help='Purity level of the gold product',
    )
    
    gold_type = fields.Selection(
        selection=[
            ('jewellery_local', 'Jewellery - Local'),
            ('jewellery_foreign', 'Jewellery - Foreign'),
            ('bars', 'Bars'),
            ('ingots', 'Ingots'),
            ('coins', 'Coins'),
        ],
        string='Gold Type',
        help='Type of gold product. Determines markup per gram from settings.',
    )
    
    gold_markup_value = fields.Float(
        string='Gold Markup Value (Deprecated)',
        digits=(16, 4),
        help='DEPRECATED: Markup is now set in Gold Pricing Settings per gold type.',
    )
    
    gold_cost_price = fields.Float(
        string='Gold Cost Price',
        digits=(16, 2),
        compute='_compute_gold_prices',
        store=True,
        help='Computed cost price: weight × base_price × purity_factor',
    )
    
    gold_min_sale_price = fields.Float(
        string='Gold Minimum Sale Price',
        digits=(16, 2),
        compute='_compute_gold_prices',
        store=True,
        help='Minimum allowed sale price: cost + (markup × 0.5)',
    )
    
    is_gold_product = fields.Boolean(
        string='Is Gold Product',
        compute='_compute_is_gold_product',
        store=True,
        help='Automatically set to True if gold_weight_g is set',
    )

    @api.depends('gold_weight_g')
    def _compute_is_gold_product(self):
        """Mark product as gold product if weight is set"""
        for record in self:
            record.is_gold_product = bool(record.gold_weight_g and record.gold_weight_g > 0)

    @api.depends('gold_weight_g', 'gold_purity', 'gold_type')
    def _compute_gold_prices(self):
        """Compute gold cost price and minimum sale price"""
        gold_price_service = self.env['gold.price.service']
        base_gold_price = gold_price_service.get_current_gold_price()
        
        # Get markup from config
        config = self.env['ir.config_parameter'].sudo()
        
        # Purity factors mapping
        purity_factors = {
            '24K': 0.999,
            '21K': 0.875,
            '18K': 0.750,
            '14K': 0.583,
            '10K': 0.417,
        }
        
        for record in self:
            if not record.is_gold_product or not record.gold_purity or not record.gold_type:
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0
                continue
            
            # Get markup per gram from settings based on gold type
            markup_param_key = f'gold_pricing.markup_{record.gold_type}'
            markup_per_gram = float(config.get_param(markup_param_key, '0.0'))
            
            if markup_per_gram <= 0:
                # Skip if markup not configured for this type
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0
                continue
            
            # Use Decimal for precise calculations
            weight = Decimal(str(record.gold_weight_g or 0))
            base_price = Decimal(str(base_gold_price))
            purity_factor = Decimal(str(purity_factors.get(record.gold_purity, 0)))
            markup = Decimal(str(markup_per_gram))
            
            # Calculate cost: GoldPricePerGram × weight (adjusted for purity)
            # GoldPricePerGram is adjusted by purity factor
            adjusted_gold_price = base_price * purity_factor
            cost = (adjusted_gold_price * weight).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            # Calculate markup total: markup × weight
            markup_total = (markup * weight).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            # Calculate total price: cost + markup_total
            total_price = (cost + markup_total).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            # Calculate minimum sale price: cost + (markup_total × 0.5)
            min_sale_price = (cost + (markup_total * Decimal('0.5'))).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            record.gold_cost_price = float(cost)
            record.gold_min_sale_price = float(min_sale_price)

    @api.constrains('gold_weight_g', 'gold_type', 'gold_purity')
    def _check_gold_required_fields(self):
        """Ensure required fields are set for gold products"""
        for record in self:
            if record.is_gold_product:
                if not record.gold_weight_g or record.gold_weight_g <= 0:
                    raise ValidationError(
                        'Gold Weight (grams) is required and must be greater than 0 for gold products.'
                    )
                if not record.gold_purity:
                    raise ValidationError(
                        'Gold Purity is required for gold products.'
                    )
                if not record.gold_type:
                    raise ValidationError(
                        'Gold Type is required for gold products. Please select a type (Jewellery - Local, Jewellery - Foreign, Bars, Ingots, or Coins).'
                    )

    def update_gold_prices(self, base_gold_price):
        """
        Update product prices based on new gold price.
        Called by cron job for batch updates.
        Skips products missing required data (weight, purity, type).
        
        :param base_gold_price: Current base gold price per gram
        """
        if not self:
            return
        
        purity_factors = {
            '24K': 0.999,
            '21K': 0.875,
            '18K': 0.750,
            '14K': 0.583,
            '10K': 0.417,
        }
        
        # Get markup configuration
        config = self.env['ir.config_parameter'].sudo()
        
        # Filter only gold products with all required data
        gold_products = self.filtered(
            lambda p: p.is_gold_product 
            and p.gold_purity 
            and p.gold_type 
            and p.gold_weight_g 
            and p.gold_weight_g > 0
        )
        
        if not gold_products:
            return
        
        # Prepare batch update values
        update_values = []
        skipped_count = 0
        
        for product in gold_products:
            # Get markup per gram from settings based on gold type
            markup_param_key = f'gold_pricing.markup_{product.gold_type}'
            markup_per_gram = float(config.get_param(markup_param_key, '0.0'))
            
            # Skip if markup not configured for this type
            if markup_per_gram <= 0:
                skipped_count += 1
                continue
            
            # Use Decimal for precise calculations
            weight = Decimal(str(product.gold_weight_g))
            base_price = Decimal(str(base_gold_price))
            purity_factor = Decimal(str(purity_factors.get(product.gold_purity, 0)))
            markup = Decimal(str(markup_per_gram))
            
            # Skip if purity factor is invalid
            if purity_factor <= 0:
                skipped_count += 1
                continue
            
            # Calculate cost: GoldPricePerGram × weight (adjusted for purity)
            # GoldPricePerGram is adjusted by purity factor
            adjusted_gold_price = base_price * purity_factor
            cost = (adjusted_gold_price * weight).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            # Calculate markup total: markup × weight
            markup_total = (markup * weight).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            # Calculate total price: cost + markup_total
            sale_price = (cost + markup_total).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            # Calculate minimum sale price: cost + (markup_total × 0.5)
            min_sale_price = (cost + (markup_total * Decimal('0.5'))).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            update_values.append({
                'id': product.id,
                'standard_price': float(cost),
                'list_price': float(sale_price),
                'gold_cost_price': float(cost),
                'gold_min_sale_price': float(min_sale_price),
            })
        
        # Log skipped products
        if skipped_count > 0:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(
                'Skipped %d gold products due to missing data or unconfigured markup.',
                skipped_count
            )
        
        # Batch update using write
        for vals in update_values:
            product_id = vals.pop('id')
            self.browse(product_id).write(vals)

