# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import unittest.mock as mock

import odoo.tests.common as common


class TestGoldPricingCron(common.TransactionCase):
    """Verify cron job definitions and that scheduled actions run correctly."""

    def test_cron_gold_prices_record_exists_and_active(self):
        """Scheduled action for gold price updates is installed and active."""
        cron = self.env.ref(
            "gold_pricing.ir_cron_update_gold_prices",
            raise_if_not_found=False,
        )
        self.assertTrue(cron, "Gold price cron record should exist")
        self.assertTrue(cron.active, "Gold price cron should be active")
        self.assertEqual(cron.model_id.model, "gold.price.service")
        self.assertEqual(
            cron.code,
            "model.update_all_gold_product_prices()",
        )
        self.assertEqual(cron.interval_number, 10)
        self.assertEqual(cron.interval_type, "minutes")

    def test_cron_diamond_prices_record_exists_and_active(self):
        """Scheduled action for diamond price updates is installed and active."""
        cron = self.env.ref(
            "gold_pricing.ir_cron_update_diamond_prices",
            raise_if_not_found=False,
        )
        self.assertTrue(cron, "Diamond price cron record should exist")
        self.assertTrue(cron.active, "Diamond price cron should be active")
        self.assertEqual(cron.model_id.model, "diamond.price.service")
        self.assertEqual(
            cron.code,
            "model.update_all_diamond_product_prices()",
        )
        self.assertEqual(cron.interval_number, 10)
        self.assertEqual(cron.interval_type, "minutes")

    def test_update_all_diamond_product_prices_runs(self):
        """Diamond update method runs without error and returns expected structure."""
        service = self.env["diamond.price.service"]
        result = service.update_all_diamond_product_prices()
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("products_updated", result)
        self.assertIn("message", result)
        self.assertTrue(result["success"])

    def test_update_all_gold_product_prices_runs(self):
        """Gold update method runs without error when API is available (mocked)."""
        service = self.env["gold.price.service"]
        with mock.patch.object(
            type(service),
            "_fetch_gold_price_from_api",
            return_value=100.0,
        ):
            result = service.update_all_gold_product_prices()
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("products_updated", result)
        self.assertIn("base_price", result)
        self.assertIn("message", result)
        self.assertTrue(result["success"])
        self.assertEqual(result["base_price"], 100.0)
