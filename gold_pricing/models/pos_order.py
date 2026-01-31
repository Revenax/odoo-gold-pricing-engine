# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import api, models
from odoo.exceptions import ValidationError

from ..utils import get_markup_per_gram


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _order_fields(self, ui_order):
        """
        Override to validate gold product prices before order creation.
        This is the backend validation that cannot be bypassed.
        """
        order_fields = super()._order_fields(ui_order)

        # Validate each line for gold products
        lines_data = ui_order.get('lines', [])
        for line_data in lines_data:
            product_id = line_data[2].get('product_id')
            discount = line_data[2].get('discount', 0)

            if product_id:
                product = self.env['product.product'].browse(product_id)
                if product.is_gold_product:
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
                        markup_per_gram = get_markup_per_gram(
                            self.env,
                            product.gold_type,
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

        return order_fields

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

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

