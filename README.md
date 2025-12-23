# Gold Pricing Engine - Odoo 17 Module

Production-grade custom Odoo 17 Community module for jewelry and gold businesses with automated pricing, POS enforcement, and live API integration.

## Overview

This module provides comprehensive gold product pricing management for jewelry businesses, including:

- **Automated Price Updates**: Fetches live gold prices from external API every 10 minutes
- **Dynamic Pricing**: Calculates product prices based on weight, purity, and markup
- **POS Price Enforcement**: Prevents sales below minimum price with backend and frontend validation
- **Batch Processing**: Efficient updates for large product catalogs (~1500 products)
- **Precision Calculations**: Uses Decimal arithmetic to avoid floating-point errors

## Module Structure

```
gold_pricing/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── product_template.py      # Product model extensions
│   ├── gold_price_service.py    # API service and cron logic
│   └── pos_order.py             # POS backend validation
├── views/
│   └── product_template_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── gold_pricing_security.xml
├── data/
│   └── gold_pricing_cron.xml     # Cron job definition
└── static/
    └── src/
        └── js/
            └── pos_discount_override.js  # POS frontend patches
```

## Installation

### Prerequisites

- Odoo 17 Community Edition (self-hosted)
- Python 3.10 or higher
- `requests` library (usually included with Odoo)

### Steps

1. **Copy Module to Odoo Addons Directory**

   ```bash
   # Navigate to your Odoo addons directory
   cd /path/to/odoo/addons
   
   # Copy the gold_pricing module
   cp -r /path/to/gold_pricing gold_pricing
   ```

2. **Update Module List**

   - Log in to Odoo as Administrator
   - Go to **Apps** menu
   - Click **Update Apps List**
   - Remove **Apps** filter to see all modules

3. **Install Module**

   - Search for "Gold Pricing Engine"
   - Click **Install**

4. **Configure API Settings** (Required)

   After installation, configure the gold price API:

   - Go to **Settings** → **Technical** → **Parameters** → **System Parameters**
   - Create/Update the following parameters:

     | Key | Value | Description |
     |-----|-------|-------------|
     | `gold_pricing.api_url` | `https://your-api.com/gold/price` | Gold price API endpoint |
     | `gold_pricing.api_key` | `your-api-key` | API authentication key (if required) |
     | `gold_pricing.fallback_price` | `75.0` | Fallback price when API is unavailable |

   **Alternative**: Use Odoo shell to set parameters:

   ```python
   self.env['ir.config_parameter'].sudo().set_param('gold_pricing.api_url', 'https://your-api.com/gold/price')
   self.env['ir.config_parameter'].sudo().set_param('gold_pricing.api_key', 'your-api-key')
   self.env['ir.config_parameter'].sudo().set_param('gold_pricing.fallback_price', '75.0')
   ```

5. **Verify Cron Job**

   - Go to **Settings** → **Technical** → **Automation** → **Scheduled Actions**
   - Find "Update Gold Product Prices"
   - Ensure it's **Active** and scheduled to run every 10 minutes

## Usage

### Setting Up Gold Products

1. **Navigate to Products**

   - Go to **Inventory** → **Products** → **Products**

2. **Create or Edit Product**

   - Create a new product or open an existing one
   - Fill in standard product fields (name, category, etc.)

3. **Configure Gold Pricing Fields**

   - **Gold Weight (grams)**: Enter the weight of gold in grams (required)
   - **Gold Purity**: Select purity level (24K, 21K, 18K, 14K, 10K) (required)
   - **Gold Markup Value**: Enter fixed markup amount (required)

4. **Automatic Calculations**

   Once weight, purity, and markup are set:
   - `gold_cost_price` = weight × base_price × purity_factor
   - `list_price` = cost_price + markup
   - `gold_min_sale_price` = cost_price + (markup × 0.5)
   - `standard_price` = cost_price

### Price Updates

Prices are automatically updated every 10 minutes via cron job:

- Fetches latest gold price from configured API
- Updates all gold products in batches of 100
- Logs execution details to Odoo logs

**Manual Update** (if needed):

```python
# Via Odoo shell
self.env['gold.price.service'].update_all_gold_product_prices()
```

### POS Price Enforcement

The module enforces pricing rules at both backend and frontend levels:

**Backend Validation** (Cannot be bypassed):
- Validates order lines before order creation
- Blocks orders with prices below `gold_min_sale_price`
- Prevents discounts exceeding 50% of markup

**Frontend Validation** (User experience):
- Prevents setting prices below minimum
- Limits discount percentage automatically
- Shows clear error messages to POS users

**Discount Rules**:
- Maximum discount = 50% of markup value
- Final price must be ≥ `gold_min_sale_price`
- System automatically adjusts invalid discounts

## API Integration

### Expected API Response Format

The module expects a JSON response with one of these formats:

```json
{
  "price_per_gram": 75.50,
  "currency": "USD",
  "timestamp": "2026-01-01T12:00:00Z"
}
```

Or:

```json
{
  "price": 75.50
}
```

Or:

```json
{
  "rate": 75.50
}
```

The module will automatically extract the price from any of these fields.

### API Authentication

If your API requires authentication, set the `gold_pricing.api_key` parameter. The module will send it as:

```
Authorization: Bearer <api_key>
```

### Error Handling

- If API is unavailable, module uses `gold_pricing.fallback_price`
- All errors are logged to Odoo logs
- Cron job continues even if individual updates fail

## Purity Factors

The module uses the following purity factors:

| Purity | Factor | Description |
|--------|--------|-------------|
| 24K | 0.999 | 99.9% pure gold |
| 21K | 0.875 | 87.5% pure gold |
| 18K | 0.750 | 75.0% pure gold |
| 14K | 0.583 | 58.3% pure gold |
| 10K | 0.417 | 41.7% pure gold |

## Security

### Access Control

- **Gold Pricing User**: Can view gold pricing information
- **Gold Pricing Manager**: Can configure pricing settings
- **System Administrators**: Can view cost prices (hidden from other users)

### Field Visibility

- `gold_cost_price`: Only visible to system administrators
- `gold_min_sale_price`: Visible to all users
- Other gold fields: Visible based on user permissions

## Performance Considerations

- **Batch Updates**: Products updated in batches of 100
- **Stored Computed Fields**: Prices are stored, not computed on-the-fly
- **Decimal Precision**: Uses Python Decimal for accurate calculations
- **Efficient Queries**: Only processes gold products (filtered by `is_gold_product`)

## Troubleshooting

### Prices Not Updating

1. **Check Cron Job Status**
   - Settings → Technical → Automation → Scheduled Actions
   - Verify "Update Gold Product Prices" is active

2. **Check API Configuration**
   - Verify API URL and key in System Parameters
   - Test API endpoint manually

3. **Check Logs**
   - Settings → Technical → Logging → Log Entries
   - Filter by "gold.price.service"

### POS Validation Errors

1. **Verify Product Configuration**
   - Ensure weight, purity, and markup are set
   - Check that `gold_min_sale_price` is calculated

2. **Check Discount Limits**
   - Maximum discount = 50% of markup
   - Final price must be ≥ minimum sale price

### API Connection Issues

1. **Test API Manually**
   ```bash
   curl -H "Authorization: Bearer YOUR_KEY" https://your-api.com/gold/price
   ```

2. **Check Fallback Price**
   - Verify `gold_pricing.fallback_price` is set
   - Module will use this if API fails

3. **Review Network Settings**
   - Ensure Odoo server can reach API endpoint
   - Check firewall rules

## Development

### Extending the Module

**Add Custom Purity Levels**:

Edit `models/product_template.py`:

```python
gold_purity = fields.Selection(
    selection=[
        # ... existing options ...
        ('22K', '22K (91.7% pure)'),
    ],
    # ...
)
```

Update purity factors in `_compute_gold_prices` and `update_gold_prices` methods.

**Modify Pricing Formula**:

Edit calculation logic in:
- `models/product_template.py` → `_compute_gold_prices()`
- `models/product_template.py` → `update_gold_prices()`

**Custom API Integration**:

Modify `models/gold_price_service.py` → `_fetch_gold_price_from_api()` to match your API response format.

## Testing

### Manual Testing Checklist

- [ ] Create gold product with weight, purity, markup
- [ ] Verify prices are calculated correctly
- [ ] Test cron job execution (manual trigger)
- [ ] Test POS order with valid price
- [ ] Test POS order with price below minimum (should fail)
- [ ] Test discount application (should respect limits)
- [ ] Verify cost price is hidden from non-admin users
- [ ] Test API fallback when API is unavailable

## Support

For issues or questions:

1. Check Odoo logs: Settings → Technical → Logging
2. Review cron job execution history
3. Verify API configuration and connectivity
4. Test with fallback price to isolate API issues

## License

**PROPRIETARY - ALL RIGHTS RESERVED**

This software is proprietary and confidential. All rights reserved.

Copyright (c) 2026 Revenax Digital Services, Mohamed A. Abdallah

See [LICENSE](LICENSE) file for full terms and conditions.

**Restrictions:**
- No copying, modification, or distribution without explicit written permission
- No reverse engineering or decompilation
- No removal of copyright notices
- Use is restricted to authorized installations only

## Version

17.0.1.0.0

## Author

**Mohamed A. Abdallah**  
Revenax Digital Services  
Website: https://www.revenax.com

---

**Note**: This module is designed for self-hosted Odoo 17 installations. It is not compatible with Odoo Online or Odoo.sh without modifications.
