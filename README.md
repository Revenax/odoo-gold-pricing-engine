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
├── utils.py                      # Pure helper functions (price parsing, computation)
├── models/
│   ├── __init__.py
│   ├── product_template.py      # Product model extensions
│   ├── gold_price_service.py    # API service and cron logic
│   ├── gold_pricing_config.py  # Configuration settings
│   └── pos_order.py             # POS backend validation
├── views/
│   ├── gold_pricing_config_views.xml
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

4. **Configure Gold Pricing Settings** (Required)

   After installation, configure the module settings:

   - Go to **Settings** → **Gold Pricing** (or search for "Gold Pricing" in Settings)
   - Configure the following:

     **API Configuration:**
     - **Gold API Endpoint**: URL endpoint for fetching gold prices
     - **Gold API Cookie**: Cookie value for API authentication
     - **Fallback Gold Price**: Price per gram when API is unavailable

     **Markup per Gram by Gold Type:**
     - **Jewellery (Local)**: Markup per gram for local jewellery
     - **Jewellery (Foreign)**: Markup per gram for foreign jewellery
     - **Bars**: Markup per gram for gold bars
     - **Ingots**: Markup per gram for gold ingots
     - **Coins**: Markup per gram for gold coins

   **Alternative**: Use Odoo shell to set parameters:

   ```python
   # API Configuration
   self.env['ir.config_parameter'].sudo().set_param('gold_api_endpoint', 'https://your-api.com/gold/price')
   self.env['ir.config_parameter'].sudo().set_param('gold_api_cookie', 'your-cookie-value')
   self.env['ir.config_parameter'].sudo().set_param('gold_pricing.fallback_price', '75.0')
   
   # Markup Configuration
   self.env['ir.config_parameter'].sudo().set_param('gold_pricing.markup_jewellery_local', '5.0')
   self.env['ir.config_parameter'].sudo().set_param('gold_pricing.markup_jewellery_foreign', '7.0')
   self.env['ir.config_parameter'].sudo().set_param('gold_pricing.markup_bars', '3.0')
   self.env['ir.config_parameter'].sudo().set_param('gold_pricing.markup_ingots', '4.0')
   self.env['ir.config_parameter'].sudo().set_param('gold_pricing.markup_coins', '6.0')
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
   - **Gold Type**: Select type (Jewellery - Local, Jewellery - Foreign, Bars, Ingots, Coins) (required)

4. **Automatic Calculations**

   Once weight, purity, and type are set:
   - Markup per gram is retrieved from settings based on gold type
   - `gold_cost_price` = (GoldPricePerGram × purity_factor) × weight
   - `markup_total` = markup_per_gram (from settings) × weight
   - `list_price` = cost_price + markup_total
   - `gold_min_sale_price` = cost_price + (markup_total × 0.5)
   - `standard_price` = cost_price

   **Note**: Products missing weight, purity, or type will be skipped during price updates.

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

The module expects HTML/text responses with Arabic content. Expected pattern:

```
علما بأن سعر البيع لجرام الذهب عيار 21 هو 5415 جنيها
```

The module extracts the 21K gold price using regex pattern: `الذهب عيار 21 هو \d+`

Example: From the text above, it extracts `5415` as the 21K gold price per gram.

### API Authentication

The module uses cookie-based authentication. Set `gold_api_cookie` parameter. The module will:

- Send the cookie in the request headers
- Include browser-like headers for compatibility
- Parse HTML/text responses with Arabic text support

Cookie format examples:

- Single cookie: `session_id=abc123`
- Multiple cookies: `session_id=abc123; auth_token=xyz789`

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
   - Verify `gold_api_endpoint` and `gold_api_cookie` in System Parameters
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
   curl -H "Cookie: YOUR_COOKIE" https://your-api.com/gold/price
   ```

2. **Check Fallback Price**
   - Verify `gold_pricing.fallback_price` is set (optional, default: 75.0)
   - Module will use this if API fails

3. **Review Network Settings**
   - Ensure Odoo server can reach API endpoint
   - Check firewall rules

## Pre-Deployment Checks

Before deploying to production, run the automated checks to ensure code quality:

### Quick Start

1. **Install development dependencies:**
   ```bash
   make install-dev
   # or
   pip install -r requirements-dev.txt
   ```

2. **Install git hooks (recommended):**
   ```bash
   ./scripts/install-git-hooks.sh
   ```
   This installs a pre-push hook that automatically runs checks before pushing.

3. **Run all checks manually:**
   ```bash
   make check
   # or
   ./scripts/ci.sh
   ```

### What Gets Checked

- **Linting**: Code style and common errors (via `ruff`)
- **Tests**: Unit tests for price parsing and computation logic (via `pytest`)
- **Type Checking**: Type annotations validation (via `mypy`)

### Manual Deployment Workflow

1. Make your changes locally
2. Run `make check` to verify everything passes
3. Commit and push to `main` branch
4. SSH into EC2 instance
5. Navigate to module directory: `cd /path/to/odoo/addons/gold_pricing`
6. Pull latest changes: `git pull origin main`
7. Restart Odoo service (method depends on your setup)

### Automated Deployment (CI/CD)

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that:
1. Runs all checks on every push and pull request
2. Automatically deploys to EC2 when checks pass on `main` branch

#### Setup Instructions

1. **Configure GitHub Secrets** (Settings → Secrets and variables → Actions):
   - `EC2_HOST`: Your EC2 instance hostname or IP (e.g., `ec2-xxx.compute.amazonaws.com`)
   - `EC2_USER`: SSH username (e.g., `ec2-user`, `ubuntu`, `admin`)
   - `EC2_SSH_KEY`: Private SSH key content for EC2 access
   - `EC2_MODULE_PATH`: Path where Odoo expects the module (deploy target), e.g. `/opt/odoo/custom-addons/gold_pricing`
   - `EC2_GIT_REPO_PATH` (optional): Path to the git repo on the server if different from the module path, e.g. `/opt/odoo/custom-addons/odoo-gold-pricing-engine`. If unset, `EC2_MODULE_PATH` is used for both pull and deploy (repo and module in the same place).
   - `EC2_ODOO_RESTART_CMD` (optional): Command to restart Odoo after deploy, e.g. `sudo systemctl restart odoo`. If unset, Odoo is not restarted automatically (restart manually). The deploy user must have passwordless sudo for this command (see below).

   **Auto-restart (sudoers):** On the EC2 instance, allow the deploy user to restart Odoo without a password:
   ```bash
   sudo visudo
   ```
   Add this line (adjust `ubuntu` and `odoo` if your user or service name differs):
   ```
   ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart odoo
   ```
   Save and exit. Then set `EC2_ODOO_RESTART_CMD=sudo systemctl restart odoo` in GitHub Secrets and/or `.env`.

2. **Give the deploy user access to both paths** (avoids "Permission denied" on `cd`):
   CI runs as `EC2_USER` (e.g. `ubuntu`) and must be able to `cd` into the **git repo path** (pull) and write to the **deploy target** (copy). **Recommended: fix permissions** (no sudo in the pipeline).
   - **Option A (recommended):** On the EC2 instance, make the deploy user able to traverse and write:
     ```bash
     # Traverse to repo and deploy target (e.g. repo name != module name):
     sudo chmod o+x /opt /opt/odoo /opt/odoo/custom-addons
     sudo chown -R ubuntu:ubuntu /opt/odoo/custom-addons/odoo-gold-pricing-engine   # git repo (pull here)
     sudo mkdir -p /opt/odoo/custom-addons/gold_pricing
     sudo chown -R ubuntu:ubuntu /opt/odoo/custom-addons/gold_pricing               # deploy target (Odoo module path)
     ```
     Deploy will `git pull` in the repo path, then copy `gold_pricing/` to the deploy target.
   - **Option B (use sudo):** Run the remote deploy script with sudo so it can cd into a root-owned path. That requires passwordless sudo for the deploy user (e.g. `ubuntu ALL=(ALL) NOPASSWD: /bin/bash` or a wrapper script in sudoers). In `.github/workflows/deploy.yml`, change the SSH run to pass the script to `sudo bash -s` instead of `bash -s`. Note: the repo will then be updated as root; ensure the Odoo process user can read the files (e.g. world/group read or run a chown in the script).

3. **Generate SSH Key** (if needed):
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy
   # Add public key to EC2: ~/.ssh/github_deploy.pub → ~/.ssh/authorized_keys on EC2
   # Add private key to GitHub Secrets: EC2_SSH_KEY
   ```

4. **Test the Workflow**:
   - Push a small change to `main`
   - Check Actions tab in GitHub to see deployment progress
   - Verify deployment on EC2

#### Deployment Process

The automated deployment:
- ✅ Runs all pre-deployment checks first
- ✅ Only deploys if all checks pass
- ✅ Pulls in the git repo path, then copies `gold_pricing/` to the deploy target (when repo path ≠ module path)
- ✅ Uses `git pull --ff-only` for atomic updates (prevents conflicts)
- ✅ Validates Python syntax before completing
- ✅ Restarts Odoo automatically if `EC2_ODOO_RESTART_CMD` is set (e.g. `sudo systemctl restart odoo`); otherwise restart manually

#### Disabling Auto-Deploy

To disable automatic deployment but keep checks:
- Edit `.github/workflows/deploy.yml`
- Comment out or remove the `deploy` job
- Checks will still run on every push/PR

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
Website: <https://www.revenax.com/>

---

**Note**: This module is designed for self-hosted Odoo 17 installations. It is not compatible with Odoo Online or Odoo.sh without modifications.
