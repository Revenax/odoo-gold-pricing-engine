# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com
# Migrate gold_type from ingots/coins to bars so reduced selection remains valid.


def migrate(cr, version):
    del version  # unused
    cr.execute("""
        UPDATE product_template
        SET gold_type = 'bars'
        WHERE gold_type IN ('ingots', 'coins')
    """)
    cr.execute("""
        UPDATE pos_order_line
        SET gold_type = 'bars'
        WHERE gold_type IN ('ingots', 'coins')
    """)
    cr.execute("""
        UPDATE account_move_line
        SET gold_type = 'bars'
        WHERE gold_type IN ('ingots', 'coins')
    """)
