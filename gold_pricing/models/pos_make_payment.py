# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com
# Require-customer logic adapted from OCA pos_customer_required.

from odoo import _, models
from odoo.exceptions import UserError


class PosMakePayment(models.TransientModel):
    _inherit = "pos.make.payment"

    def check(self):
        order = self.env["pos.order"].browse(
            self.env.context.get("active_id", False)
        )
        if (
            order
            and not order.partner_id
            and order.session_id.config_id.require_customer != "no"
        ):
            raise UserError(
                _(
                    "An anonymous order cannot be confirmed.\n"
                    "Please select a customer for this order."
                )
            )
        return super().check()
