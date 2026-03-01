#!/usr/bin/env python3
"""
Fetch silver 999 price from dahabmasr.com (Selenium; page is JS-rendered).

Run: .venv/bin/python scripts/selenium_automation.py

For Odoo: Configure Silver API Endpoint + Silver 999 Regex in Settings.
If your source returns static HTML, Odoo fetches via HTTP like gold.
If the source is JS-rendered (e.g. dahabmasr), use an external job to fetch
and expose an HTTP endpoint, or run this script and set the fallback manually.
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
_PRICE_NUMERIC = re.compile(r"[\d,]+(?:\.\d+)?")


def _parse_price(text):
    if not text or not text.strip():
        return None
    m = _PRICE_NUMERIC.search(text.strip().replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _text_ready(driver):
    el = driver.find_element(By.XPATH, PRICE_CELL_XPATH)
    t = el.text.strip() if el.text else ""
    return el if t and t != "--" else False


def create_driver():
    opts = Options()
    if os.environ.get("HEADLESS", "1") != "0":
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_experimental_option(
        "prefs",
        {"profile.managed_default_content_settings.images": 2, "profile.default_content_setting_values.images": 2},
    )
    for a in ("--disable-extensions", "--disable-plugins", "--disable-sync", "--disable-translate",
              "--disable-background-networking", "--no-first-run", "--log-level=3"):
        opts.add_argument(a)
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(10)
    return d


def main():
    driver = create_driver()
    try:
        driver.get(SILVER_PAGE)
        el = WebDriverWait(driver, 30).until(_text_ready)
        price = _parse_price(el.text)
        if price is not None:
            print("Silver 999:", price)
            return price
        print("Silver 999:", el.text.strip())
        return None
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
