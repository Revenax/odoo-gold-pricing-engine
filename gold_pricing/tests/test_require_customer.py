# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com
# Behaviour aligned with OCA pos_customer_required.

import odoo.tests.common as common
from odoo.exceptions import ValidationError


class TestPosRequireCustomer(common.TransactionCase):
    """Test require_customer constraint on pos.order (compliance with pos_customer_required)."""

    def setUp(self):
        super().setUp()
        self.pos_config = self.env.ref("point_of_sale.pos_config_main").copy()

    def test_customer_not_required(self):
        self.pos_config.require_customer = "no"
        pos_session = self.env["pos.session"].create(
            {"user_id": self.env.uid, "config_id": self.pos_config.id}
        )
        self.env["pos.order"].create(
            {
                "session_id": pos_session.id,
                "partner_id": False,
                "amount_tax": 0.0,
                "amount_total": 0.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
            }
        )

    def test_customer_required_order_rejects_anonymous(self):
        self.pos_config.require_customer = "order"
        pos_session = self.env["pos.session"].create(
            {"user_id": self.env.uid, "config_id": self.pos_config.id}
        )
        with self.assertRaises(ValidationError):
            self.env["pos.order"].create(
                {
                    "session_id": pos_session.id,
                    "partner_id": False,
                    "amount_tax": 0.0,
                    "amount_total": 0.0,
                    "amount_paid": 0.0,
                    "amount_return": 0.0,
                }
            )

    def test_customer_required_payment_rejects_anonymous(self):
        self.pos_config.require_customer = "payment"
        pos_session = self.env["pos.session"].create(
            {"user_id": self.env.uid, "config_id": self.pos_config.id}
        )
        with self.assertRaises(ValidationError):
            self.env["pos.order"].create(
                {
                    "session_id": pos_session.id,
                    "partner_id": False,
                    "amount_tax": 0.0,
                    "amount_total": 0.0,
                    "amount_paid": 0.0,
                    "amount_return": 0.0,
                }
            )
