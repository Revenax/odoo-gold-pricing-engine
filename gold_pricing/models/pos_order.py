# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..utils import get_markup_per_gram

# Same selections as product.template for gold fields on order line
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
]


class PosOrder(models.Model):
    _inherit = 'pos.order'

    require_customer = fields.Selection(
        related="session_id.config_id.require_customer",
    )

    @api.constrains("partner_id", "session_id")
    def _check_partner(self):
        for rec in self:
            if rec.require_customer != "no" and not rec.partner_id:
                raise ValidationError(
                    _("Customer is required for this order and is missing.")
                )

    def _enrich_order_line_vals_with_gold(self, line_vals):
        """
        Add gold-specific fields to a single order line vals dict when the
        product is a gold product. Used when building order from UI.
        """
        product_id = line_vals.get('product_id')
        if not product_id:
            return
        product = self.env['product.product'].browse(product_id)
        if not product.exists() or not getattr(product, 'is_gold_product', False):
            return
        line_vals['gold_purity'] = product.gold_purity
        line_vals['gold_weight_g'] = product.gold_weight_g or 0.0
        line_vals['gold_type'] = product.gold_type
        line_vals['making_fee'] = getattr(product, 'making_fee', 0.0) or 0.0
        try:
            gold_price_service = self.env['gold.price.service']
            line_vals['gold_price_per_gram'] = (
                gold_price_service.get_current_gold_price()
            )
        except Exception as e:
            raise ValidationError(
                _('Could not fetch gold price for order line. '
                  'Please check gold price settings. Details: %s') % str(e)
            ) from e

    @api.model
    def _order_fields(self, ui_order):
        """
        Override to validate gold product prices before order creation and to
        populate gold-specific fields on each order line from product and price
        service.
        """
        order_fields = super()._order_fields(ui_order)

        # Validate each line for gold products
        lines_data = ui_order.get('lines', [])
        for line_data in lines_data:
            if len(line_data) < 3 or not isinstance(line_data[2], dict):
                continue
            line_vals = line_data[2]
            product_id = line_vals.get('product_id')
            price_unit = line_vals.get('price_unit', 0)
            discount = line_vals.get('discount', 0)

            if product_id:
                product = self.env['product.product'].browse(product_id)
                if not product.exists():
                    continue
                if getattr(product, 'is_gold_product', False):
                    # Enforce minimum sale price
                    if product.gold_min_sale_price:
                        final_price = price_unit * (1 - discount / 100.0)
                        if final_price < product.gold_min_sale_price:
                            raise ValidationError(
                                f'Cannot sell {product.name} below minimum price of '
                                f'{product.gold_min_sale_price:.2f}. '
                                f'Current price: {final_price:.2f}'
                            )

                    # Check if discount exceeds 50% of markup
                    # Markup total = markup per gram × weight (from settings)
                    has_weight = product.gold_weight_g and product.gold_weight_g > 0
                    if product.gold_type and has_weight:
                        weight_for_markup = (
                            product.gold_weight_g if product.gold_type == 'bars' else None
                        )
                        markup_per_gram = get_markup_per_gram(
                            self.env,
                            product.gold_type,
                            weight_g=weight_for_markup,
                        )

                        if markup_per_gram > 0 and product.list_price > 0:
                            markup_total = markup_per_gram * product.gold_weight_g
                            max_discount_percent = (
                                markup_total * 0.5 / product.list_price
                            ) * 100
                            if discount > max_discount_percent:
                                raise ValidationError(
                                    f'Discount for {product.name} cannot exceed '
                                    f'{max_discount_percent:.2f}% (50% of markup). '
                                    f'Current discount: {discount:.2f}%'
                                )

        # Populate gold fields on each order line from product and price service
        for line_cmd in order_fields.get('lines') or []:
            if len(line_cmd) >= 3 and isinstance(line_cmd[2], dict):
                self._enrich_order_line_vals_with_gold(line_cmd[2])

        return order_fields

    @api.model
    def _get_invoice_lines_values(self, line_values, pos_order_line):
        """
        Pass gold-specific fields from POS order line to invoice line so the
        invoice report can display them.
        """
        result = super()._get_invoice_lines_values(line_values, pos_order_line)
        product = pos_order_line.product_id
        if not product or not getattr(product, 'is_gold_product', False):
            return result
        gold_fields = [
            'gold_purity', 'gold_weight_g', 'gold_type',
            'gold_price_per_gram', 'making_fee',
        ]
        for fname in gold_fields:
            if hasattr(pos_order_line, fname):
                result[fname] = pos_order_line[fname]
        return result

    def _process_saved_order(self, draft):
        """Require invoice for every order when finalizing (not draft)."""
        if not draft and not self.to_invoice:
            raise UserError(
                _(
                    "An invoice must be set for every order. "
                    "Please enable invoicing for this order before paying."
                )
            )
        return super()._process_saved_order(draft)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    gold_purity = fields.Selection(
        selection=GOLD_PURITY_SELECTION,
        string='Gold Purity',
        help='Gold purity at order time (copied from product).',
    )
    gold_weight_g = fields.Float(
        string='Gold Weight (g)',
        digits=(16, 2),
        help='Gold weight in grams at order time (copied from product).',
    )
    gold_type = fields.Selection(
        selection=GOLD_TYPE_SELECTION,
        string='Gold Type',
        help='Gold type at order time (copied from product).',
    )
    gold_price_per_gram = fields.Float(
        string='Gold Price per Gram',
        digits=(16, 4),
        help='Gold price per gram at sale time (from price service).',
    )
    making_fee = fields.Float(
        string='Making Fee',
        digits=(16, 2),
        default=0.0,
        help='Making fee for this line (from product or overridden).',
    )

    @api.constrains('price_unit', 'discount')
    def _check_gold_minimum_price(self):
        """
        Constraint to ensure gold products are not sold below minimum price.
        """
        for line in self:
            if line.product_id.is_gold_product and line.product_id.gold_min_sale_price:
                final_price = line.price_unit * (1 - line.discount / 100.0)

                if final_price < line.product_id.gold_min_sale_price:
                    raise ValidationError(
                        f'Cannot sell {line.product_id.name} below minimum price of '
                        f'{line.product_id.gold_min_sale_price:.2f}. '
                        f'Current price: {final_price:.2f}'
                    )
