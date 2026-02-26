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
    ]

    JEWELLERY_TYPE_SELECTION = [
        ('gold_local', 'Gold - Local'),
        ('gold_foreign', 'Gold - Foreign'),
        ('gold_bars', 'Gold Bars'),
        ('diamond_jewellery', 'Diamond Jewellery'),
        ('silver', 'Silver'),
    ]

    GOLD_TYPE_SELECTION = [
        ('jewellery_local', 'Jewellery - Local'),
        ('jewellery_foreign', 'Jewellery - Foreign'),
        ('bars', 'Bars'),
    ]

    SILVER_PURITY_SELECTION = [
        ('999.0', '999.0'),
        ('999.9', '999.9'),
    ]

    JEWELLERY_TYPE_TO_GOLD_TYPE = {
        'gold_local': 'jewellery_local',
        'gold_foreign': 'jewellery_foreign',
        'gold_bars': 'bars',
    }
    GOLD_TYPE_TO_JEWELLERY_TYPE = {
        value: key for key, value in JEWELLERY_TYPE_TO_GOLD_TYPE.items()
    }

    VALID_GOLD_PURITIES = {item[0] for item in GOLD_PURITY_SELECTION}
    VALID_GOLD_TYPES = {item[0] for item in GOLD_TYPE_SELECTION}
    VALID_JEWELLERY_TYPES = {item[0] for item in JEWELLERY_TYPE_SELECTION}
    VALID_SILVER_PURITY = {item[0] for item in SILVER_PURITY_SELECTION}
    MAX_GOLD_WEIGHT_G = 100000
    GOLD_PRICE_UPDATE_FIELDS = {
        'jewellery_type',
        'jewellery_weight_g',
        'gold_weight_g',
        'gold_purity',
        'gold_type',
    }
    DIAMOND_PRICE_UPDATE_FIELDS = {'jewellery_type', 'diamond_usd_price'}

    jewellery_type = fields.Selection(
        selection=JEWELLERY_TYPE_SELECTION,
        string='Jewellery Type',
        help='Select the jewellery category to apply pricing rules.',
    )

    jewellery_weight_g = fields.Float(
        string='Jewellery Weight (grams)',
        digits=(16, 2),
        help='Total jewellery weight in grams.',
    )

    # Gold-specific fields
    gold_weight_g = fields.Float(
        string='Gold Weight (grams)',
        digits=(16, 2),
        help='Legacy gold weight field. Automatically synced from Jewellery Weight for gold products.',
    )

    gold_purity = fields.Selection(
        selection=GOLD_PURITY_SELECTION,
        string='Jewellery Karat (Gold)',
        help='Purity level of the gold product',
    )

    gold_type = fields.Selection(
        selection=GOLD_TYPE_SELECTION,
        string='Gold Type (Internal)',
        help='Internal gold type used by existing markup configuration.',
    )

    diamond_karat = fields.Char(
        string='Jewellery Karat (Diamond)',
        help='Open field for diamond karat/grade information.',
    )

    silver_purity = fields.Selection(
        selection=SILVER_PURITY_SELECTION,
        string='Jewellery Karat (Silver)',
        help='Purity level for silver jewellery.',
    )

    def _register_hook(self):
        super()._register_hook()
        # One-time cleanup: convert deprecated ingots/coins to bars so stored values
        # match the reduced selection (avoids ValueError when opening old records).
        if self._name != 'product.template':
            return
        cr = self.env.cr
        cr.execute(
            "SELECT 1 FROM product_template WHERE gold_type IN ('ingots','coins') LIMIT 1"
        )
        if cr.fetchone():
            cr.execute(
                "UPDATE product_template SET gold_type = 'bars' "
                "WHERE gold_type IN ('ingots','coins')"
            )
            cr.execute(
                "UPDATE pos_order_line SET gold_type = 'bars' "
                "WHERE gold_type IN ('ingots','coins')"
            )
            cr.execute(
                "UPDATE account_move_line SET gold_type = 'bars' "
                "WHERE gold_type IN ('ingots','coins')"
            )
            _logger.info(
                'jewellery_evaluator: migrated gold_type ingots/coins to bars (runtime cleanup)'
            )
        cr.execute(
            "UPDATE product_template SET jewellery_type = 'gold_bars' "
            "WHERE jewellery_type IS NULL AND gold_type = 'bars'"
        )
        cr.execute(
            "UPDATE product_template SET jewellery_type = 'gold_local' "
            "WHERE jewellery_type IS NULL AND gold_type = 'jewellery_local'"
        )
        cr.execute(
            "UPDATE product_template SET jewellery_type = 'gold_foreign' "
            "WHERE jewellery_type IS NULL AND gold_type = 'jewellery_foreign'"
        )
        cr.execute(
            "UPDATE product_template SET jewellery_weight_g = gold_weight_g "
            "WHERE (jewellery_weight_g IS NULL OR jewellery_weight_g = 0) "
            "AND gold_weight_g > 0"
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
        help='Minimum allowed sale price: cost + (markup × 0.7)',
    )

    is_gold_product = fields.Boolean(
        string='Is Gold Product',
        compute='_compute_is_gold_product',
        store=True,
        help='Automatically set to True for gold jewellery types.',
    )

    diamond_usd_price = fields.Float(
        string='Diamond USD Ticket Price',
        digits=(16, 2),
        help='Diamond price in USD. Updating this sets standard and sale prices.',
    )

    is_diamond_product = fields.Boolean(
        string='Is Diamond Product',
        compute='_compute_is_diamond_product',
        store=True,
        help='Automatically set to True for diamond jewellery type.',
    )

    is_silver_product = fields.Boolean(
        string='Is Silver Product',
        compute='_compute_is_silver_product',
        store=True,
        help='Automatically set to True for silver jewellery type.',
    )

    @api.depends('jewellery_type')
    def _compute_is_gold_product(self):
        """Mark product as gold product based on jewellery type."""
        for record in self:
            record.is_gold_product = bool(
                record.jewellery_type in self.JEWELLERY_TYPE_TO_GOLD_TYPE
            )

    @api.depends('jewellery_type')
    def _compute_is_diamond_product(self):
        """Mark product as diamond product based on jewellery type."""
        for record in self:
            record.is_diamond_product = bool(
                record.jewellery_type == 'diamond_jewellery'
            )

    @api.depends('jewellery_type')
    def _compute_is_silver_product(self):
        """Mark product as silver product based on jewellery type."""
        for record in self:
            record.is_silver_product = bool(record.jewellery_type == 'silver')

    def _map_jewellery_type_to_gold_type(self, jewellery_type):
        return self.JEWELLERY_TYPE_TO_GOLD_TYPE.get(jewellery_type)

    def _normalize_jewellery_vals(self, vals):
        normalized = dict(vals)

        if not normalized.get('jewellery_type'):
            legacy_gold_type = normalized.get('gold_type')
            if legacy_gold_type in self.GOLD_TYPE_TO_JEWELLERY_TYPE:
                normalized['jewellery_type'] = self.GOLD_TYPE_TO_JEWELLERY_TYPE[legacy_gold_type]

        if 'jewellery_weight_g' not in normalized and 'gold_weight_g' in normalized:
            normalized['jewellery_weight_g'] = normalized.get('gold_weight_g')

        jewellery_type = normalized.get('jewellery_type')
        if jewellery_type in self.JEWELLERY_TYPE_TO_GOLD_TYPE:
            normalized['gold_type'] = self._map_jewellery_type_to_gold_type(jewellery_type)
            if 'jewellery_weight_g' in normalized:
                normalized['gold_weight_g'] = normalized.get('jewellery_weight_g') or 0.0
        elif 'jewellery_type' in normalized:
            normalized['gold_type'] = False
            normalized['gold_weight_g'] = 0.0

        return normalized

    @api.depends('jewellery_type', 'jewellery_weight_g', 'gold_purity', 'gold_type')
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
            if not record.is_gold_product:
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0
                continue
            if not record.jewellery_weight_g or record.jewellery_weight_g <= 0:
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0
                continue
            if not record.gold_purity:
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0
                continue

            # Get markup per gram from settings (bars use weight-tier lookup)
            internal_gold_type = record._map_jewellery_type_to_gold_type(record.jewellery_type)
            if not internal_gold_type:
                record.gold_cost_price = 0.0
                record.gold_min_sale_price = 0.0
                continue

            weight_for_markup = record.jewellery_weight_g if internal_gold_type == 'bars' else None
            markup_per_gram = get_markup_per_gram(
                self.env, internal_gold_type, weight_g=weight_for_markup
            )

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
                    weight_g=record.jewellery_weight_g or 0,
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

        if not self.is_gold_product:
            return {}
        if not self.jewellery_weight_g or self.jewellery_weight_g <= 0:
            return {}
        if not self.gold_purity:
            return {}

        internal_gold_type = self._map_jewellery_type_to_gold_type(self.jewellery_type)
        if not internal_gold_type:
            return {}

        weight_for_markup = self.jewellery_weight_g if internal_gold_type == 'bars' else None
        markup_per_gram = get_markup_per_gram(
            self.env, internal_gold_type, weight_g=weight_for_markup
        )
        if markup_per_gram <= 0:
            return {}

        try:
            cost_price, sale_price, _min_sale_price = compute_gold_product_price(
                base_gold_price_21k=base_gold_price,
                purity=self.gold_purity,
                weight_g=self.jewellery_weight_g or 0,
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

    @api.onchange('jewellery_type', 'jewellery_weight_g')
    def _onchange_sync_gold_legacy_fields(self):
        for record in self:
            if record.jewellery_type in self.JEWELLERY_TYPE_TO_GOLD_TYPE:
                record.gold_type = record._map_jewellery_type_to_gold_type(record.jewellery_type)
                record.gold_weight_g = record.jewellery_weight_g or 0.0
            elif record.jewellery_type:
                record.gold_type = False
                record.gold_weight_g = 0.0

    @api.onchange('jewellery_type', 'jewellery_weight_g', 'gold_purity')
    def _onchange_jewellery_evaluator_fields(self):
        """Update prices immediately in the UI when gold fields change."""
        try:
            gold_price_service = self.env['gold.price.service']
            base_gold_price = gold_price_service.get_current_gold_price()
            for record in self:
                if not record.is_gold_product:
                    continue
                update_vals = record._get_gold_price_update_vals(
                    base_gold_price)
                if update_vals:
                    record.update(update_vals)
        except Exception as e:
            raise ValidationError(
                _('Gold price could not be updated. Please try again or check '
                  'gold price settings. Details: %s') % str(e)
            ) from e

    @api.onchange('jewellery_type', 'diamond_usd_price')
    def _onchange_diamond_pricing_fields(self):
        """Update prices immediately in the UI when diamond price changes."""
        try:
            for record in self:
                if not record.is_diamond_product:
                    continue
                update_vals = record._get_diamond_price_update_vals()
                if update_vals:
                    record.update(update_vals)
        except Exception as e:
            raise ValidationError(
                _('Diamond price could not be updated. Details: %s') % str(e)
            ) from e

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = [self._normalize_jewellery_vals(vals) for vals in vals_list]
        records = super().create(normalized_vals_list)
        try:
            if not self.env.context.get('skip_gold_price_update'):
                if any(
                    self.GOLD_PRICE_UPDATE_FIELDS & vals.keys()
                    for vals in normalized_vals_list
                ):
                    gold_price_service = self.env['gold.price.service']
                    base_gold_price = gold_price_service.get_current_gold_price()
                    for record in records:
                        if not record.is_gold_product:
                            continue
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
                    for vals in normalized_vals_list
                ):
                    for record in records:
                        if not record.is_diamond_product:
                            continue
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
        normalized_vals = self._normalize_jewellery_vals(vals)
        res = super().write(normalized_vals)
        try:
            if not self.env.context.get('skip_gold_price_update'):
                if self.GOLD_PRICE_UPDATE_FIELDS & set(normalized_vals.keys()):
                    gold_price_service = self.env['gold.price.service']
                    base_gold_price = (
                        gold_price_service.get_current_gold_price()
                    )
                    for record in self:
                        if not record.is_gold_product:
                            continue
                        update_vals = record._get_gold_price_update_vals(
                            base_gold_price
                        )
                        if update_vals:
                            record.with_context(
                                skip_gold_price_update=True
                            ).write(update_vals)

            if not self.env.context.get('skip_diamond_price_update'):
                if self.DIAMOND_PRICE_UPDATE_FIELDS & set(normalized_vals.keys()):
                    for record in self:
                        if not record.is_diamond_product:
                            continue
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

    @api.constrains('jewellery_type', 'jewellery_weight_g', 'gold_purity', 'silver_purity', 'gold_type')
    def _check_gold_required_fields(self):
        """Ensure required fields are set for each jewellery type."""
        for record in self:
            if record.jewellery_type and record.jewellery_type not in self.VALID_JEWELLERY_TYPES:
                raise ValidationError(
                    f'Invalid jewellery type: {record.jewellery_type}.'
                )

            if record.is_gold_product:
                if not record.jewellery_weight_g or record.jewellery_weight_g <= 0:
                    raise ValidationError(
                        'Jewellery Weight (grams) is required and must be greater than 0 for gold products.'
                    )
                if record.jewellery_weight_g > self.MAX_GOLD_WEIGHT_G:
                    raise ValidationError(
                        'Jewellery Weight (grams) cannot exceed 100,000 grams (100 kg). '
                        'Please verify the weight value.'
                    )
                if not record.gold_purity:
                    raise ValidationError(
                        'Jewellery Karat is required for gold products.'
                    )
                if record.gold_purity not in self.VALID_GOLD_PURITIES:
                    raise ValidationError(
                        f'Invalid gold purity: {record.gold_purity}. '
                        f'Must be one of: {", ".join(sorted(self.VALID_GOLD_PURITIES))}'
                    )
                expected_gold_type = record._map_jewellery_type_to_gold_type(record.jewellery_type)
                if not record.gold_type or record.gold_type != expected_gold_type:
                    raise ValidationError(
                        'Internal Gold Type is not synchronized with Jewellery Type.'
                    )
                if record.gold_type not in self.VALID_GOLD_TYPES:
                    raise ValidationError(
                        f'Invalid gold type: {record.gold_type}. '
                        f'Must be one of: {", ".join(sorted(self.VALID_GOLD_TYPES))}'
                    )

            if record.is_silver_product and not record.silver_purity:
                raise ValidationError(
                    'Jewellery Karat is required for silver products.'
                )
            if record.silver_purity and record.silver_purity not in self.VALID_SILVER_PURITY:
                raise ValidationError(
                    f'Invalid silver purity: {record.silver_purity}. '
                    f'Must be one of: {", ".join(sorted(self.VALID_SILVER_PURITY))}'
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
            and p.jewellery_weight_g
            and p.jewellery_weight_g > 0
        )

        if not gold_products:
            return

        # Prepare batch update values
        update_values = []
        skipped_count = 0

        for product in gold_products:
            internal_gold_type = product._map_jewellery_type_to_gold_type(product.jewellery_type)
            if not internal_gold_type:
                skipped_count += 1
                continue
            weight_for_markup = product.jewellery_weight_g if internal_gold_type == 'bars' else None
            markup_per_gram = get_markup_per_gram(
                self.env, internal_gold_type, weight_g=weight_for_markup
            )

            # Skip if markup not configured for this type
            if markup_per_gram <= 0:
                skipped_count += 1
                continue

            # Use pure helper function to compute prices
            try:
                cost_price, sale_price, min_sale_price = compute_gold_product_price(
                    base_gold_price_21k=base_gold_price,
                    purity=product.gold_purity,
                    weight_g=product.jewellery_weight_g,
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
