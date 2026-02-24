# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_gold_invoice_lines(self):
        """
        Return invoice lines that have gold-specific data (for report).
        Used by the gold invoice report template.
        Excludes section/note/rounding lines; includes product lines
        (display_type 'product' or False) that have gold data.
        """
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda line: line.display_type not in (
                'line_section', 'line_note', 'rounding'
            )
            and (line.gold_weight_g or line.gold_purity)
        )
