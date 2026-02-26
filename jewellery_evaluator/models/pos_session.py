# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_config(self):
        params = super()._loader_params_pos_config()
        search_params = params.get("search_params") or {}
        fields = search_params.get("fields")
        # When parent uses fields=[] it means "all fields"; only extend when
        # parent explicitly lists fields so require_customer is included.
        if isinstance(fields, list) and len(fields) > 0 and "require_customer" not in fields:
            params.setdefault("search_params", {})[
                "fields"] = fields + ["require_customer"]
        return params

    def _loader_params_product_product(self):
        params = super()._loader_params_product_product()
        fields = list(params.get('search_params', {}).get('fields', []))

        gold_fields = [
            'jewellery_type',
            'jewellery_weight_g',
            'diamond_karat',
            'silver_purity',
            'gold_min_sale_price',
            'gold_cost_price',
            'gold_weight_g',
            'gold_purity',
            'gold_type',
            'is_gold_product',
            'is_diamond_product',
            'is_silver_product',
        ]

        for field_name in gold_fields:
            if field_name not in fields:
                fields.append(field_name)

        params.setdefault('search_params', {})['fields'] = fields
        return params
