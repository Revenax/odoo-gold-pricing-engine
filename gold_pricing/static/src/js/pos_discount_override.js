/** @odoo-module **/
/**
 * Copyright 2026 Revenax Digital Services
 * Author: Mohamed A. Abdallah
 * Website: https://www.revenax.com
 */

import { Orderline } from "@point_of_sale/app/store/models";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/**
 * Override POS discount functionality to enforce gold pricing rules.
 * This prevents discounts that would violate minimum sale price requirements.
 */
patch(Orderline.prototype, {
  /**
   * Override set_discount to enforce gold product pricing rules.
   * Maximum discount is limited to 50% of markup value.
   */
  set_discount(discount) {
    if (!this.product || !this.product.is_gold_product) {
      return super.set_discount(...arguments);
    }

    const product = this.product;
    const currentPrice = this.get_unit_price();
    const listPrice = product.list_price || currentPrice;
    const costPrice = product.gold_cost_price || 0;
    const weight = product.gold_weight_g || 0;
    const minSalePrice = product.gold_min_sale_price || 0;

    if (costPrice <= 0 || weight <= 0 || minSalePrice <= 0) {
      return super.set_discount(...arguments);
    }

    // Calculate markup total from list price and cost price
    // markup_total = list_price - cost_price
    const markupTotal = listPrice - costPrice;
    const maxDiscountPercent =
      listPrice > 0 ? ((markupTotal * 0.5) / listPrice) * 100 : 0;
    const clampedDiscount = Math.min(discount, maxDiscountPercent);
    const finalPrice = currentPrice * (1 - clampedDiscount / 100.0);

    if (finalPrice < minSalePrice) {
      const maxDiscountForMinPrice =
        ((currentPrice - minSalePrice) / currentPrice) * 100;
      const finalDiscount = Math.max(
        0,
        Math.min(clampedDiscount, maxDiscountForMinPrice)
      );

      if (finalDiscount < discount) {
        this.pos.notification.add(
          _t(
            `Discount for ${
              product.display_name
            } cannot exceed ${finalDiscount.toFixed(
              2
            )}% to maintain minimum sale price of ${minSalePrice.toFixed(2)}.`
          ),
          { type: "warning" }
        );
      }

      return super.set_discount(finalDiscount);
    }

    if (clampedDiscount < discount) {
      this.pos.notification.add(
        _t(
          `Maximum discount for ${
            product.display_name
          } is ${maxDiscountPercent.toFixed(2)}% (50% of markup).`
        ),
        { type: "warning" }
      );
    }

    return super.set_discount(clampedDiscount);
  },

  /**
   * Override set_unit_price to prevent setting price below minimum.
   */
  set_unit_price(price) {
    if (this.product && this.product.is_gold_product) {
      const minSalePrice = this.product.gold_min_sale_price || 0;

      if (minSalePrice > 0 && price < minSalePrice) {
        this.pos.notification.add(
          _t(
            `Price for ${
              this.product.display_name
            } cannot be below minimum sale price of ${minSalePrice.toFixed(2)}.`
          ),
          { type: "danger" }
        );
        price = minSalePrice;
      }
    }

    return super.set_unit_price(price);
  },

  /**
   * Override compute_all to ensure final price respects minimum.
   */
  compute_all() {
    const result = super.compute_all(...arguments);

    if (this.product && this.product.is_gold_product) {
      const minSalePrice = this.product.gold_min_sale_price || 0;
      const finalPrice = result.price || 0;

      if (minSalePrice > 0 && finalPrice < minSalePrice) {
        const priceDiff = minSalePrice - finalPrice;
        const discountAdjustment = (priceDiff / this.get_unit_price()) * 100;

        if (this.discount < discountAdjustment) {
          this.set_discount(0);
          this.set_unit_price(minSalePrice);

          this.pos.notification.add(
            _t(
              `Price adjusted to minimum sale price of ${minSalePrice.toFixed(
                2
              )} for ${this.product.display_name}.`
            ),
            { type: "warning" }
          );

          return super.compute_all(...arguments);
        }
      }
    }

    return result;
  },
});

/**
 * Override ProductScreen to add validation when clicking discount button.
 */
patch(ProductScreen.prototype, {
  /**
   * Override clickDiscount to add validation for gold products.
   */
  async clickDiscount() {
    const order = this.pos.get_order();
    const selectedLine = order.get_selected_orderline();

    if (
      selectedLine &&
      selectedLine.product &&
      selectedLine.product.is_gold_product
    ) {
      const product = selectedLine.product;
      const minSalePrice = product.gold_min_sale_price || 0;
      const currentPrice = selectedLine.get_unit_price();
      const listPrice = product.list_price || currentPrice;
      const costPrice = product.gold_cost_price || 0;

      if (minSalePrice > 0 && costPrice > 0) {
        // Calculate markup total from list price and cost price
        const markupTotal = listPrice - costPrice;
        const maxDiscountPercent =
          listPrice > 0 ? ((markupTotal * 0.5) / listPrice) * 100 : 0;
        const maxDiscountForMinPrice =
          ((currentPrice - minSalePrice) / currentPrice) * 100;
        const actualMaxDiscount = Math.min(
          maxDiscountPercent,
          maxDiscountForMinPrice
        );

        if (actualMaxDiscount <= 0) {
          this.pos.notification.add(
            _t(
              `Cannot apply discount to ${product.display_name}. Price is already at minimum.`
            ),
            { type: "warning" }
          );
          return;
        }
      }
    }

    return super.clickDiscount(...arguments);
  },
});
