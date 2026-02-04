# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gold_api_endpoint = fields.Char(
        string='Gold API Endpoint',
        config_parameter='gold_pricing.gold_api_endpoint',
        help='URL endpoint for fetching gold prices from the API',
    )

    gold_api_cookie = fields.Char(
        string='Gold API Cookie',
        config_parameter='gold_pricing.gold_api_cookie',
        help='Cookie value for API authentication',
    )

    fallback_price = fields.Float(
        string='Fallback Gold Price',
        config_parameter='gold_pricing.fallback_price',
        digits=(16, 2),
        default=75.0,
        help='Fallback gold price per gram when API is unavailable',
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

    markup_bars = fields.Float(
        string='Markup per Gram - Bars',
        config_parameter='gold_pricing.markup_bars',
        digits=(16, 4),
        default=0.0,
        help='Markup per gram for gold bars',
    )

    markup_ingots = fields.Float(
        string='Markup per Gram - Ingots',
        config_parameter='gold_pricing.markup_ingots',
        digits=(16, 4),
        default=0.0,
        help='Markup per gram for gold ingots',
    )

    markup_coins = fields.Float(
        string='Markup per Gram - Coins',
        config_parameter='gold_pricing.markup_coins',
        digits=(16, 4),
        default=0.0,
        help='Markup per gram for gold coins',
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

    def get_markup_for_type(self, gold_type):
        """
        Get markup per gram for a specific gold type.

        :param gold_type: Gold type string (jewellery_local, jewellery_foreign, bars, ingots, coins)
        :return: float - Markup per gram
        """
        markup_map = {
            'jewellery_local': self.markup_jewellery_local,
            'jewellery_foreign': self.markup_jewellery_foreign,
            'bars': self.markup_bars,
            'ingots': self.markup_ingots,
            'coins': self.markup_coins,
        }
        return markup_map.get(gold_type, 0.0)
