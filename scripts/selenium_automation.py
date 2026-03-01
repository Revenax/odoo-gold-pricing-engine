#!/usr/bin/env python3
"""
Copyright Mohamed A. Abdallah @ 2026
Revenax Digital Services
Website: https://www.revenax.com
"""

import os
import re
import sys
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:
    print("Selenium not installed. Run: pip install -r requirements-dev.txt")
    sys.exit(1)

SILVER_PAGE = "https://dahabmasr.com/silver-price-today-en"
PRICE_CELL_XPATH = "/html/body/div[3]/main/div[2]/div/div[2]/section/div/div[2]/div[1]/table/tbody/tr[1]/td[3]"

# Extract first number (digits and optional decimal/comma) from scraped text
_PRICE_NUMERIC = re.compile(r"[\d,]+(?:\.\d+)?")


def _parse_price_from_text(text):
    """Extract numeric price from cell text (e.g. '165EGP' or '1,234.56')."""
    if not text or not text.strip():
        return None
    s = text.strip().replace(",", "")
    m = _PRICE_NUMERIC.search(s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _text_not_placeholder(driver):
    el = driver.find_element(By.XPATH, PRICE_CELL_XPATH)
    return el if el.text.strip() and el.text.strip() != "--" else False


def create_driver():
    opts = Options()
    if os.environ.get("HEADLESS", "1") != "0":
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
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
        "--disable-plugins-discovery",
        "--disable-sync",
        "--disable-translate",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-component-update",
        "--disable-domain-reliability",
        "--disable-client-side-phishing-detection",
        "--disable-hang-monitor",
        "--disable-prompt-on-repost",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-background-timer-throttling",
        "--no-first-run",
        "--no-service-autorun",
        "--password-store=basic",
        "--use-mock-keychain",
        "--disable-features=TranslateUI,BackForwardCache",
        "--metrics-recording-only",
        "--safebrowsing-disable-auto-update",
        "--log-level=3",
    ):
        opts.add_argument(a)
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(10)
    return d


def main():
    driver = create_driver()
    try:
        driver.get(SILVER_PAGE)
        el = WebDriverWait(driver, 30).until(_text_not_placeholder)
        raw = el.text.strip()
        price = _parse_price_from_text(raw)
        if price is not None:
            print("Silver 999:", price)
            return price
        print("Silver 999:", raw)
        return raw
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
