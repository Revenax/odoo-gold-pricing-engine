# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..utils import compute_gold_product_price, get_markup_per_gram  # noqa: E402

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    GOLD_PURITY_SELECTION = [
        ('24K', '24K'),
        ('21K', '21K'),
        ('18K', '18K'),
        ('14K', '14K'),
        ('10K', '10K'),
    ]

    GOLD_TYPE_SELECTION = [
        ('jewellery_local', 'Jewellery - Local'),
        ('jewellery_foreign', 'Jewellery - Foreign'),
        ('bars', 'Bars'),
        ('ingots', 'Ingots'),
        ('coins', 'Coins'),
    ]

    VALID_GOLD_PURITIES = {item[0] for item in GOLD_PURITY_SELECTION}
    VALID_GOLD_TYPES = {item[0] for item in GOLD_TYPE_SELECTION}
    MAX_GOLD_WEIGHT_G = 100000
    GOLD_PRICE_UPDATE_FIELDS = {'gold_weight_g', 'gold_purity', 'gold_type'}
    DIAMOND_PRICE_UPDATE_FIELDS = {'diamond_usd_price'}

    # Gold-specific fields
    gold_weight_g = fields.Float(
        string='Gold Weight (grams)',
        digits=(16, 4),
        help='Weight of gold in grams. Required for gold products.',
    )

    gold_purity = fields.Selection(
        selection=GOLD_PURITY_SELECTION,
        string='Gold Purity',
        help='Purity level of the gold product',
    )

    gold_type = fields.Selection(
        selection=GOLD_TYPE_SELECTION,
        string='Gold Type',
        help='Type of gold product. Determines markup per gram from settings.',
    )

    making_fee = fields.Float(
        string='Making Fee',
        digits=(16, 2),
        default=0.0,
        help='Default making fee for this gold product. Can be overridden on the order line.',
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

    diamond_usd_price = fields.Float(
        string='Diamond USD Price',
        digits=(16, 2),
        help='Diamond price in USD. Updating this sets standard and sale prices.',
    )

    is_diamond_product = fields.Boolean(
        string='Is Diamond Product',
        compute='_compute_is_diamond_product',
        store=True,
        help='Automatically set to True if Diamond USD Price is set',
    )

    @api.depends('gold_weight_g')
    def _compute_is_gold_product(self):
        """Mark product as gold product if weight is set"""
        for record in self:
            record.is_gold_product = bool(
                record.gold_weight_g and record.gold_weight_g > 0)

    @api.depends('diamond_usd_price')
    def _compute_is_diamond_product(self):
        """Mark product as diamond product if USD price is set"""
        for record in self:
            record.is_diamond_product = bool(
                record.diamond_usd_price and record.diamond_usd_price > 0)

    @api.depends('gold_weight_g', 'gold_purity', 'gold_type')
    def _compute_gold_prices(self):
        """Compute gold cost price and minimum sale price"""
        gold_price_service = self.env['gold.price.service']
        try:
            base_gold_price = gold_price_service.get_current_gold_price()
        except Exception as e:
            _logger.warning(
                'Gold price service failed in _compute_gold_prices: %s',
                str(e),
                exc_info=True,
            )
            base_gold_price = 0.0

        for record in self:
            if not record.gold_weight_g or record.gold_weight_g <= 0:
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0
                continue
            if not record.gold_purity or not record.gold_type:
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0
                continue

            # Get markup per gram from settings based on gold type
            markup_per_gram = get_markup_per_gram(self.env, record.gold_type)

            if markup_per_gram <= 0:
                # Skip if markup not configured for this type
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0
                continue

            # Use pure helper function to compute prices
            try:
                cost_price, sale_price, min_sale_price = compute_gold_product_price(
                    base_gold_price_21k=base_gold_price,
                    purity=record.gold_purity,
                    weight_g=record.gold_weight_g or 0,
                    markup_per_gram=markup_per_gram,
                )
                record.gold_cost_price = cost_price
                record.gold_min_sale_price = min_sale_price
            except ValueError:
                # Invalid purity or other error
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0

    def _get_gold_price_update_vals(self, base_gold_price):
        """
        Prepare standard and list price updates for gold products.

        Args:
            base_gold_price: Base 21K gold price per gram

        Returns:
            dict: Fields to update, or empty dict if not applicable
        """
        self.ensure_one()

        if not self.gold_weight_g or self.gold_weight_g <= 0:
            return {}
        if not self.gold_purity or not self.gold_type:
            return {}

        markup_per_gram = get_markup_per_gram(self.env, self.gold_type)
        if markup_per_gram <= 0:
            return {}

        try:
            cost_price, sale_price, _min_sale_price = compute_gold_product_price(
                base_gold_price_21k=base_gold_price,
                purity=self.gold_purity,
                weight_g=self.gold_weight_g or 0,
                markup_per_gram=markup_per_gram,
            )
        except ValueError:
            return {}

        return {
            'list_price': sale_price,
        }

    def _get_diamond_price_update_vals(self):
        """
        Prepare standard and list price updates for diamond products.

        Returns:
            dict: Fields to update, or empty dict if not applicable
        """
        self.ensure_one()

        if not self.diamond_usd_price or self.diamond_usd_price <= 0:
            return {}

        diamond_price_service = self.env['diamond.price.service']
        exchange_rate = diamond_price_service.get_usd_to_egp_rate()
        discount_pct = diamond_price_service.get_global_diamond_discount()
        price_egp = (self.diamond_usd_price * exchange_rate) * \
            (100 - discount_pct) / 100.0

        return {
            'list_price': price_egp,
        }

    @api.onchange('gold_weight_g', 'gold_purity', 'gold_type')
    def _onchange_gold_pricing_fields(self):
        """Update prices immediately in the UI when gold fields change."""
        try:
            gold_price_service = self.env['gold.price.service']
            base_gold_price = gold_price_service.get_current_gold_price()
            for record in self:
                update_vals = record._get_gold_price_update_vals(
                    base_gold_price)
                if update_vals:
                    record.update(update_vals)
        except Exception as e:
            raise ValidationError(
                _('Gold price could not be updated. Please try again or check '
                  'gold price settings. Details: %s') % str(e)
            ) from e

    @api.onchange('diamond_usd_price')
    def _onchange_diamond_pricing_fields(self):
        """Update prices immediately in the UI when diamond price changes."""
        try:
            for record in self:
                update_vals = record._get_diamond_price_update_vals()
                if update_vals:
                    record.update(update_vals)
        except Exception as e:
            raise ValidationError(
                _('Diamond price could not be updated. Details: %s') % str(e)
            ) from e

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        try:
            if not self.env.context.get('skip_gold_price_update'):
                if any(
                    self.GOLD_PRICE_UPDATE_FIELDS & vals.keys()
                    for vals in vals_list
                ):
                    gold_price_service = self.env['gold.price.service']
                    base_gold_price = gold_price_service.get_current_gold_price()
                    for record in records:
                        update_vals = record._get_gold_price_update_vals(
                            base_gold_price
                        )
                        if update_vals:
                            record.with_context(
                                skip_gold_price_update=True
                            ).write(update_vals)

            if not self.env.context.get('skip_diamond_price_update'):
                if any(
                    self.DIAMOND_PRICE_UPDATE_FIELDS & vals.keys()
                    for vals in vals_list
                ):
                    for record in records:
                        update_vals = record._get_diamond_price_update_vals()
                        if update_vals:
                            record.with_context(
                                skip_diamond_price_update=True
                            ).write(update_vals)
        except Exception as e:
            raise ValidationError(
                _('Product price update failed. Please check gold/diamond '
                  'settings or try again. Details: %s') % str(e)
            ) from e
        return records

    def write(self, vals):
        res = super().write(vals)
        try:
            if not self.env.context.get('skip_gold_price_update'):
                if self.GOLD_PRICE_UPDATE_FIELDS & set(vals.keys()):
                    gold_price_service = self.env['gold.price.service']
                    base_gold_price = (
                        gold_price_service.get_current_gold_price()
                    )
                    for record in self:
                        update_vals = record._get_gold_price_update_vals(
                            base_gold_price
                        )
                        if update_vals:
                            record.with_context(
                                skip_gold_price_update=True
                            ).write(update_vals)

            if not self.env.context.get('skip_diamond_price_update'):
                if self.DIAMOND_PRICE_UPDATE_FIELDS & set(vals.keys()):
                    for record in self:
                        update_vals = record._get_diamond_price_update_vals()
                        if update_vals:
                            record.with_context(
                                skip_diamond_price_update=True
                            ).write(update_vals)
        except Exception as e:
            raise ValidationError(
                _('Product price update failed. Please check gold/diamond '
                  'settings or try again. Details: %s') % str(e)
            ) from e
        return res

    @api.constrains('gold_weight_g', 'gold_type', 'gold_purity')
    def _check_gold_required_fields(self):
        """Ensure required fields are set for gold products"""
        for record in self:
            if record.is_gold_product:
                if not record.gold_weight_g or record.gold_weight_g <= 0:
                    raise ValidationError(
                        'Gold Weight (grams) is required and must be greater than 0 for gold products.'
                    )
                if record.gold_weight_g > self.MAX_GOLD_WEIGHT_G:
                    raise ValidationError(
                        'Gold Weight (grams) cannot exceed 100,000 grams (100 kg). '
                        'Please verify the weight value.'
                    )
                if not record.gold_purity:
                    raise ValidationError(
                        'Gold Purity is required for gold products.'
                    )
                if record.gold_purity not in self.VALID_GOLD_PURITIES:
                    raise ValidationError(
                        f'Invalid gold purity: {record.gold_purity}. '
                        f'Must be one of: {", ".join(sorted(self.VALID_GOLD_PURITIES))}'
                    )
                if not record.gold_type:
                    raise ValidationError(
                        'Gold Type is required for gold products. '
                        'Please select a type (Jewellery - Local, '
                        'Jewellery - Foreign, Bars, Ingots, or Coins).'
                    )
                if record.gold_type not in self.VALID_GOLD_TYPES:
                    raise ValidationError(
                        f'Invalid gold type: {record.gold_type}. '
                        f'Must be one of: {", ".join(sorted(self.VALID_GOLD_TYPES))}'
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
            markup_per_gram = get_markup_per_gram(self.env, product.gold_type)

            # Skip if markup not configured for this type
            if markup_per_gram <= 0:
                skipped_count += 1
                continue

            # Use pure helper function to compute prices
            try:
                cost_price, sale_price, min_sale_price = compute_gold_product_price(
                    base_gold_price_21k=base_gold_price,
                    purity=product.gold_purity,
                    weight_g=product.gold_weight_g,
                    markup_per_gram=markup_per_gram,
                )
                update_values.append({
                    'record': product,
                    'list_price': sale_price,
                    'gold_cost_price': cost_price,
                    'gold_min_sale_price': min_sale_price,
                })
            except ValueError:
                # Invalid purity or other error - skip this product
                skipped_count += 1
                continue

        # Log skipped products
        if skipped_count > 0:
            _logger.warning(
                'Skipped %d gold products due to missing data or unconfigured markup.',
                skipped_count
            )

        # Batch update using write
        for vals in update_values:
            product = vals.pop('record')
            product.write(vals)
