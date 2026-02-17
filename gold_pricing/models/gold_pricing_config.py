# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gold_api_endpoint = fields.Char(
        string='Gold API Endpoint',
        config_parameter='gold_pricing.gold_api_endpoint',
        help='URL endpoint for fetching gold prices from the API',
    )

    gold_21k_regex_formula = fields.Char(
        string='Gold 21K Regex Formula',
        config_parameter='gold_pricing.gold_21k_regex_formula',
        help='Regular expression applied to the API HTML response to extract the 21K gold '
             'price per gram. Use one capturing group for the price number (e.g. (\\d+(?:\\.\\d+)?)). '
             'If no group, the full match is used.',
    )

    fallback_price = fields.Float(
        string='Fallback Gold Price',
        config_parameter='gold_pricing.fallback_price',
        digits=(16, 2),
        default=75.0,
        help='Fallback gold price per gram when API is unavailable. '
             'Automatically updated to the last fetched price whenever the API returns successfully.',
    )

    markup_jewellery_local = fields.Float(
        string='Markup per Gram - Jewellery (Local)',
        config_parameter='gold_pricing.markup_jewellery_local',
        digits=(16, 4),
        default=0.0,
        help='Markup per gram for local jewellery',
    )

    markup_jewellery_foreign = fields.Float(
        string='Markup per Gram - Jewellery (Foreign)',
        config_parameter='gold_pricing.markup_jewellery_foreign',
        digits=(16, 4),
        default=0.0,
        help='Markup per gram for foreign jewellery',
    )

    # Bars: weight-tiered markup (EGP per gram). Weights 1, 2.5, 5, 10, 20, 31, 50, 100, 250, 500, 1000g+.
    markup_bars_1g = fields.Float(
        string='Bars 1g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_1g',
        digits=(16, 4),
        default=200.0,
        help='Markup per gram for bars up to 1g',
    )
    markup_bars_2_5g = fields.Float(
        string='Bars 2.5g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_2_5g',
        digits=(16, 4),
        default=200.0,
        help='Markup per gram for 2.5g tier',
    )
    markup_bars_5g = fields.Float(
        string='Bars 5g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_5g',
        digits=(16, 4),
        default=125.0,
        help='Markup per gram for 5g tier',
    )
    markup_bars_10g = fields.Float(
        string='Bars 10g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_10g',
        digits=(16, 4),
        default=120.0,
        help='Markup per gram for 10g tier',
    )
    markup_bars_20g = fields.Float(
        string='Bars 20g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_20g',
        digits=(16, 4),
        default=120.0,
        help='Markup per gram for 20g tier',
    )
    markup_bars_31g = fields.Float(
        string='Bars 31g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_31g',
        digits=(16, 4),
        default=115.0,
        help='Markup per gram for 31g tier',
    )
    markup_bars_50g = fields.Float(
        string='Bars 50g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_50g',
        digits=(16, 4),
        default=100.0,
        help='Markup per gram for 50g tier',
    )
    markup_bars_100g = fields.Float(
        string='Bars 100g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_100g',
        digits=(16, 4),
        default=100.0,
        help='Markup per gram for 100g tier',
    )
    markup_bars_250g = fields.Float(
        string='Bars 250g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_250g',
        digits=(16, 4),
        default=80.0,
        help='Markup per gram for 250g tier',
    )
    markup_bars_500g = fields.Float(
        string='Bars 500g (EGP/g)',
        config_parameter='gold_pricing.markup_bars_500g',
        digits=(16, 4),
        default=80.0,
        help='Markup per gram for 500g tier',
    )
    markup_bars_1000g = fields.Float(
        string='Bars 1000g+ (EGP/g)',
        config_parameter='gold_pricing.markup_bars_1000g',
        digits=(16, 4),
        default=80.0,
        help='Markup per gram for bars 1000g and above',
    )

    global_diamond_discount = fields.Integer(
        string='Global Diamond Discount',
        config_parameter='gold_pricing.global_diamond_discount',
        default=40,
        help='Discount percentage (0-80). Sale price = (USD x USD/EGP rate) x (100 - discount) / 100. E.g. 40 = 40%% off.',
    )

    @api.constrains('global_diamond_discount')
    def _check_global_diamond_discount(self):
        for record in self:
            if record.global_diamond_discount is not False and (
                record.global_diamond_discount < 0 or record.global_diamond_discount > 80
            ):
                raise ValidationError(
                    'Global Diamond Discount must be between 0 and 80.'
                )

    pos_config_id = fields.Many2one(
        comodel_name="pos.config",
        string="Point of Sale",
        help="Select the Point of Sale to configure. Used for Require Customer and Invoicing below.",
    )
    require_customer = fields.Selection(
        selection=[
            ("no", "Optional"),
            ("payment", "Required before paying"),
            ("order", "Required before starting the order"),
        ],
        string="Require Customer",
        default="no",
        help="Require customer for orders in this point of sale.",
    )
    pos_to_invoice_by_default = fields.Boolean(
        string="Default to Invoice",
        default=False,
        help="Default behaviour for new orders: to invoice.",
    )

    @api.onchange("pos_config_id")
    def _onchange_pos_config_id(self):
        if self.pos_config_id:
            self.require_customer = self.pos_config_id.require_customer
            self.pos_to_invoice_by_default = self.pos_config_id.default_to_invoice

    def get_values(self):
        res = super().get_values()
        pos_config = self.env["pos.config"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        if pos_config:
            res["pos_config_id"] = pos_config.id
            res["require_customer"] = pos_config.require_customer
            res["pos_to_invoice_by_default"] = pos_config.default_to_invoice
        return res

    def set_values(self):
        super().set_values()
        if self.pos_config_id:
            self.pos_config_id.write({
                "require_customer": self.require_customer,
                "default_to_invoice": self.pos_to_invoice_by_default,
            })

    def get_markup_for_type(self, gold_type, weight_g=None):
        """
        Get markup per gram for a specific gold type.

        :param gold_type: Gold type (jewellery_local, jewellery_foreign, bars)
        :param weight_g: Required when gold_type is 'bars'; used for tier lookup
        :return: float - Markup per gram
        """
        if gold_type == 'jewellery_local':
            return self.markup_jewellery_local
        if gold_type == 'jewellery_foreign':
            return self.markup_jewellery_foreign
        if gold_type == 'bars':
            if weight_g is None or weight_g <= 0:
                return 0.0
            from ..utils import get_markup_per_gram
            return get_markup_per_gram(self.env, 'bars', weight_g=weight_g)
        return 0.0
