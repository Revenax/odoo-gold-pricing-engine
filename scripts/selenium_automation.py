#!/usr/bin/env python3
"""
Selenium: render dahabmasr.com, get silver 999 price from XPath element.
Optionally push to Odoo when ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD are set.

Run: ODOO_URL=... ODOO_DB=... ODOO_USER=... ODOO_PASSWORD=... .venv/bin/python scripts/selenium_automation.py
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


def _push_to_odoo(price):
    url = (os.environ.get("ODOO_URL") or "").rstrip("/")
    db, user, pwd = os.environ.get("ODOO_DB", ""), os.environ.get("ODOO_USER", ""), os.environ.get("ODOO_PASSWORD", "")
    if not url or not db or not user or not pwd:
        return False
    try:
        import xmlrpc.client
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
        uid = common.authenticate(db, user, pwd, {})
        if not uid:
            return False
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
        models.execute_kw(db, uid, pwd, "silver.price.service", "set_silver_price_999", [float(price)])
        models.execute_kw(db, uid, pwd, "silver.price.service", "update_all_silver_product_prices", [])
        return True
    except Exception:
        return False


def main():
    driver = create_driver()
    try:
        driver.get(SILVER_PAGE)
        el = WebDriverWait(driver, 30).until(_text_ready)
        price = _parse_price(el.text)
        if price is not None:
            print("Silver 999:", price)
            if _push_to_odoo(price):
                print("Odoo: updated.")
            return price
        print("Silver 999:", el.text.strip())
        return None
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
