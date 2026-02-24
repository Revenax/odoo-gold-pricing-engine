{
    'name': 'Gold Pricing Engine',
    'version': '17.0.2.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Automated gold pricing with live API updates and POS price enforcement',
    'description': """
        Gold Pricing Engine for Jewelry Business
        =========================================
        Version: 17.0.1.0.0

        This module provides:
        * Automated gold price updates from external API (every 10 minutes)
        * Product pricing based on weight, purity, and markup
        * POS price enforcement to prevent sales below minimum price
        * Real-time cost and sale price calculations

        Features:
        - Extends product.template with gold-specific fields
        - Automatic price updates via cron job
        - Backend and frontend POS validation
        - Batch processing for performance
    """,
    'author': 'Revenax Digital Services, Mohamed A. Abdallah',
    'website': 'https://www.revenax.com',
    'depends': [
        'base',
        'product',
        'point_of_sale',
        'account',
        'web',
        'stock',
    ],
    'data': [
        'gold_pricing/security/ir.model.access.csv',
        'gold_pricing/security/gold_pricing_security.xml',
        'gold_pricing/views/gold_pricing_config_views.xml',
        'gold_pricing/views/pos_config_views.xml',
        'gold_pricing/views/pos_order_views.xml',
        'gold_pricing/views/product_template_views.xml',
        'gold_pricing/views/account_move_views.xml',
        'gold_pricing/report/paperformat_gold.xml',
        'gold_pricing/report/report_invoice_gold.xml',
        'gold_pricing/report/external_layout_gold.xml',
        'gold_pricing/data/gold_pricing_cron.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'gold_pricing/static/src/js/pos_discount_override.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
