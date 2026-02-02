{
    'name': 'Gold Pricing Engine',
    'version': '17.0.1.0.0',
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
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/gold_pricing_security.xml',
        'views/gold_pricing_config_views.xml',
        'views/pos_config_views.xml',
        'views/product_template_views.xml',
        'data/gold_pricing_cron.xml',
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
