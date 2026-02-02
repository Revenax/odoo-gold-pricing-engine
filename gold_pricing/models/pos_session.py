# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_config(self):
        params = super()._loader_params_pos_config()
        fields = params.get('search_params', {}).get('fields', [])
        if 'require_customer' not in fields:
            fields = list(fields) + ['require_customer']
        params.setdefault('search_params', {})['fields'] = fields
        return params

    def _loader_params_product_product(self):
        params = super()._loader_params_product_product()
        fields = params.get('search_params', {}).get('fields', [])

        gold_fields = [
            'gold_min_sale_price',
            'gold_cost_price',
            'gold_weight_g',
            'gold_purity',
            'gold_type',
            'is_gold_product',
        ]

        for field_name in gold_fields:
            if field_name not in fields:
                fields.append(field_name)

        params.setdefault('search_params', {})['fields'] = fields
        return params
