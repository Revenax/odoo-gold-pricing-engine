# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

import logging
import re

from odoo import api, models

from ..utils import compute_silver_product_price  # noqa: E402

_logger = logging.getLogger(__name__)

# ---------- Selenium helpers (lazy-imported) ----------

_SILVER_PAGE = "https://dahabmasr.com/silver-price-today-en"
_PRICE_CELL_XPATH = (
    "/html/body/div[3]/main/div[2]/div/div[2]/section"
    "/div/div[2]/div[1]/table/tbody/tr[1]/td[3]"
)
_PRICE_NUMERIC = re.compile(r"[\d,]+(?:\.\d+)?")


def _parse_price(text):
    """Extract a numeric price from a string like '53.20 EGP'."""
    if not text or not text.strip():
        return None
    m = _PRICE_NUMERIC.search(text.strip().replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _create_driver():
    """Create a headless Chrome WebDriver (requires selenium + chromium)."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_experimental_option(
        "prefs",
        {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.images": 2,
        },
    )
    for a in (
        "--disable-extensions",
        "--disable-plugins",
        "--disable-sync",
        "--disable-translate",
        "--disable-background-networking",
        "--no-first-run",
        "--log-level=3",
    ):
        opts.add_argument(a)
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(10)
    return d


def _fetch_silver_price_selenium():
    """
    Launch headless Chrome, navigate to dahabmasr.com, and scrape silver 999
    price. Returns float or None.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    driver = _create_driver()
    try:
        driver.get(_SILVER_PAGE)

        def _text_ready(drv):
            el = drv.find_element(By.XPATH, _PRICE_CELL_XPATH)
            t = el.text.strip() if el.text else ""
            return el if t and t != "--" else False

        el = WebDriverWait(driver, 30).until(_text_ready)
        return _parse_price(el.text)
    finally:
        driver.quit()


class SilverPriceService(models.Model):
    _name = 'silver.price.service'
    _description = 'Silver Price Service'

    @api.model
    def get_current_silver_price_999(self):
        """
        Get current silver 999 price per gram from stored param.
        Value is set by the Selenium scraper (_fetch_silver_price_from_web)
        or manually in Settings.
        """
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'jewellery_evaluator.silver_fallback_price', '0.0'
        )
        try:
            val = float(str(raw).replace(',', '').strip())
            return val if val >= 0 else 0.0
        except (ValueError, TypeError):
            return 0.0

    @api.model
    def set_silver_price_999(self, price_per_gram):
        """Store silver 999 price. Called by Selenium script via RPC or internally."""
        if price_per_gram is None or price_per_gram <= 0:
            return
        self.env['ir.config_parameter'].sudo().set_param(
            'jewellery_evaluator.silver_fallback_price', str(price_per_gram)
        )
        _logger.info('Silver 999 price updated: %s per gram', price_per_gram)

    @api.model
    def _fetch_silver_price_from_web(self):
        """
        Fetch silver 999 price per gram from dahabmasr.com using Selenium.
        Stores the result in ir.config_parameter on success.

        Returns the price (float) or 0.0 on failure.
        """
        try:
            price = _fetch_silver_price_selenium()
        except ImportError:
            _logger.warning(
                'Selenium is not installed — cannot auto-fetch silver price. '
                'Install with: pip install selenium'
            )
            return 0.0
        except Exception as e:
            _logger.error(
                'Selenium silver price fetch failed: %s', e, exc_info=True)
            return 0.0

        if price is None or price <= 0:
            _logger.warning(
                'Silver price scrape returned invalid value: %s', price)
            return 0.0

        self.set_silver_price_999(price)
        _logger.info('Silver 999 price fetched from web: %s', price)
        return price

    @api.model
    def update_all_silver_product_prices(self):
        """
        Fetch silver price from web (Selenium), then update all silver products.
        Called by cron every 10 minutes and after Settings are saved.
        """
        _logger.info('Starting silver price update for all products')
        try:
            # Step 1: try to fetch fresh price from the website
            fetched = self._fetch_silver_price_from_web()
            if fetched > 0:
                base_silver = fetched
            else:
                # Fall back to last stored price
                base_silver = self.get_current_silver_price_999()

            if base_silver <= 0:
                _logger.warning(
                    'Silver price is 0 — neither Selenium nor stored value available.'
                )
                return {
                    'success': True, 'products_updated': 0,
                    'base_price': 0.0, 'message': 'Silver price not configured',
                }
            _logger.info('Silver price: %s per gram', base_silver)

            silver_products = self.env['product.template'].search([
                ('jewellery_type', '=', 'silver'),
                ('silver_purity', '!=', False),
                ('jewellery_weight_g', '>', 0),
            ])

            if not silver_products:
                _logger.info('No silver products found to update')
                return {
                    'success': True, 'products_updated': 0,
                    'base_price': base_silver, 'message': 'No silver products found',
                }

            silver_products.update_silver_prices(base_silver)
            total = len(silver_products)
            _logger.info(
                'Silver price update completed: %d products, base %s', total, base_silver)
            return {
                'success': True, 'products_updated': total,
                'base_price': base_silver, 'message': f'Updated {total} products',
            }
        except Exception as e:
            _logger.error('Silver price update failed: %s',
                          str(e), exc_info=True)
            return {
                'success': False, 'products_updated': 0,
                'base_price': None, 'message': str(e), 'error': str(e),
            }
