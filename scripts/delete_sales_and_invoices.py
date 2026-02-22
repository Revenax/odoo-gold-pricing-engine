#!/usr/bin/env python3
"""
Bulk delete all POS orders and customer invoices (for test cleanup).

Run inside Odoo shell:
  odoo shell -d YOUR_DATABASE -c /path/to/odoo.conf

Then in the shell:
  exec(open("scripts/delete_sales_and_invoices.py").read())

Or from project root with Odoo on PYTHONPATH:
  python scripts/delete_sales_and_invoices.py   # if script connects via env

This script expects to be run in an already-started Odoo shell (env, cr, uid
available). It cancels posted invoices, then unlinks invoices and POS orders
in the correct order to satisfy dependencies.
"""

def _delete_sales_and_invoices(env):
    """Delete all customer invoices and POS orders. Use env from odoo shell."""
    Move = env["account.move"]
    PosOrder = env["pos.order"]
    PosPayment = env["pos.payment"]

    # 1. Customer invoices and refunds
    domain = [("move_type", "in", ("out_invoice", "out_refund"))]
    invoices = Move.search(domain)
    if not invoices:
        print("No customer invoices found.")
    else:
        # Cancel posted so they can be deleted (if your config allows)
        posted = invoices.filtered(lambda m: m.state == "posted")
        if posted:
            try:
                posted.button_cancel()
            except Exception as e:
                print("Could not cancel some invoices: %s" % (e,))
        # Unlink draft and cancel
        to_unlink = invoices.filtered(lambda m: m.state in ("draft", "cancel"))
        n_inv = len(to_unlink)
        to_unlink.unlink()
        print("Unlinked %s customer invoice(s)." % (n_inv,))

    # 2. POS payments (must be removed before orders in some setups)
    payments = PosPayment.search([])
    n_pay = len(payments)
    if n_pay:
        payments.unlink()
        print("Unlinked %s POS payment(s)." % (n_pay,))
    else:
        print("No POS payments found.")

    # 3. POS orders (lines cascade)
    orders = PosOrder.search([])
    n_ord = len(orders)
    if n_ord:
        orders.unlink()
        print("Unlinked %s POS order(s)." % (n_ord,))
    else:
        print("No POS orders found.")

    env.cr.commit()
    print("Done. Transaction committed.")


# When run inside Odoo shell, 'env' is the environment
try:
    env
except NameError:
    print("Run this script inside Odoo shell: odoo shell -d DB -c odoo.conf")
    print("Then: exec(open('scripts/delete_sales_and_invoices.py').read())")
else:
    _delete_sales_and_invoices(env)
