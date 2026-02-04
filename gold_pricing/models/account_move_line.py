# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import fields, models

# Same selections as product.template for display on invoice
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


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    gold_purity = fields.Selection(
        selection=GOLD_PURITY_SELECTION,
        string='Gold Purity',
        help='Gold purity (Karat) for this invoice line.',
    )
    gold_weight_g = fields.Float(
        string='Gold Weight (g)',
        digits=(16, 4),
        help='Gold weight in grams for this line.',
    )
    gold_type = fields.Selection(
        selection=GOLD_TYPE_SELECTION,
        string='Gold Type',
        help='Gold type for this line.',
    )
    gold_price_per_gram = fields.Float(
        string='Gold Price per Gram',
        digits=(16, 4),
        help='Gold price per gram at sale time.',
    )
    making_fee = fields.Float(
        string='Making Fee',
        digits=(16, 2),
        default=0.0,
        help='Making fee for this line.',
    )
