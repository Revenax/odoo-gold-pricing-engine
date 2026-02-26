# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com


def migrate(cr, version):
    del version  # unused

    # Convert old records to the new Jewellery Type model.
    cr.execute("""
        UPDATE product_template
        SET jewellery_type = 'gold_local'
        WHERE jewellery_type IS NULL
          AND gold_type = 'jewellery_local'
    """)
    cr.execute("""
        UPDATE product_template
        SET jewellery_type = 'gold_foreign'
        WHERE jewellery_type IS NULL
          AND gold_type = 'jewellery_foreign'
    """)
    cr.execute("""
        UPDATE product_template
        SET jewellery_type = 'gold_bars'
        WHERE jewellery_type IS NULL
          AND gold_type = 'bars'
    """)
    cr.execute("""
        UPDATE product_template
        SET jewellery_type = 'diamond_jewellery'
        WHERE jewellery_type IS NULL
          AND COALESCE(diamond_usd_price, 0) > 0
    """)

    # Keep the new weight as the source of truth and sync legacy gold weight.
    cr.execute("""
        UPDATE product_template
        SET jewellery_weight_g = gold_weight_g
        WHERE COALESCE(jewellery_weight_g, 0) = 0
          AND COALESCE(gold_weight_g, 0) > 0
    """)

    # Gold purity support is now limited to 24K/21K/18K.
    cr.execute("""
        UPDATE product_template
        SET gold_purity = '18K'
        WHERE gold_purity IN ('14K', '10K')
    """)

    # Ensure legacy gold fields stay consistent with the new jewellery type.
    cr.execute("""
        UPDATE product_template
        SET gold_type = 'jewellery_local',
            gold_weight_g = COALESCE(jewellery_weight_g, 0)
        WHERE jewellery_type = 'gold_local'
    """)
    cr.execute("""
        UPDATE product_template
        SET gold_type = 'jewellery_foreign',
            gold_weight_g = COALESCE(jewellery_weight_g, 0)
        WHERE jewellery_type = 'gold_foreign'
    """)
    cr.execute("""
        UPDATE product_template
        SET gold_type = 'bars',
            gold_weight_g = COALESCE(jewellery_weight_g, 0)
        WHERE jewellery_type = 'gold_bars'
    """)
