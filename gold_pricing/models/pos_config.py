# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    default_to_invoice = fields.Boolean(
        string="Default to Invoice",
        default=False,
        help="Default behaviour for new orders: to invoice.",
    )
