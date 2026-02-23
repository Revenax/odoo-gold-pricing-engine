/** @odoo-module **/
/**
 * Copyright 2026 Revenax Digital Services
 * Author: Mohamed A. Abdallah
 * Website: https://www.revenax.com
 */

import { Orderline } from "@point_of_sale/app/store/models";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
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
    // When no minimum sale price is set, assume 20% max discount
    const effectiveMin =
      minSalePrice > 0 ? minSalePrice : currentPrice * 0.8;

    let maxDiscountPercent = 20;
    if (costPrice > 0 && weight > 0 && listPrice > 0) {
      const markupTotal = listPrice - costPrice;
      maxDiscountPercent =
        ((markupTotal * 0.5) / listPrice) * 100;
    }
    const clampedDiscount = Math.min(discount, maxDiscountPercent);
    let finalPrice = currentPrice * (1 - clampedDiscount / 100.0);

    if (finalPrice < effectiveMin) {
      const maxDiscountForMinPrice =
        currentPrice > 0
          ? ((currentPrice - effectiveMin) / currentPrice) * 100
          : 0;
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
            )}% to maintain minimum sale price of ${effectiveMin.toFixed(2)}.`
          ),
          { type: "warning" }
        );
      }

      return super.set_discount(finalDiscount);
    }

    if (clampedDiscount < discount) {
      this.pos.notification.add(
        _t(
          `Maximum discount for ${product.display_name} is ${maxDiscountPercent.toFixed(2)}%.`
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
      const listPrice = this.product.list_price || price;
      const effectiveMin =
        minSalePrice > 0 ? minSalePrice : listPrice * 0.8;

      if (effectiveMin > 0 && price < effectiveMin) {
        this.pos.notification.add(
          _t(
            `Price for ${
              this.product.display_name
            } cannot be below minimum sale price of ${effectiveMin.toFixed(2)}.`
          ),
          { type: "danger" }
        );
        price = effectiveMin;
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
      const unitPrice = this.get_unit_price();
      const effectiveMin =
        minSalePrice > 0 ? minSalePrice : unitPrice * 0.8;
      const finalPrice = result.price || 0;

      if (effectiveMin > 0 && finalPrice < effectiveMin) {
        const discountAdjustment =
          unitPrice > 0
            ? ((effectiveMin - finalPrice) / unitPrice) * 100
            : 0;

        if (this.discount < discountAdjustment) {
          this.set_discount(0);
          this.set_unit_price(effectiveMin);

          this.pos.notification.add(
            _t(
              `Price adjusted to minimum sale price of ${effectiveMin.toFixed(
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
 * Require customer before payment when pos.config.require_customer === "payment".
 * Require invoice for every order (to_invoice must be set).
 * Compliant with OCA pos_customer_required behaviour for customer.
 */
patch(PaymentScreen.prototype, {
  async _isOrderValid(isForceValidate) {
    if (
      this.pos.config.require_customer === "payment" &&
      !this.currentOrder.get_partner()
    ) {
      const { confirmed } = await this.popup.add(ConfirmPopup, {
        title: _t("An anonymous order cannot be confirmed"),
        body: _t("Please select a customer for this order."),
      });
      if (confirmed) {
        this.selectPartner();
      }
      return false;
    }
    if (!this.currentOrder.to_invoice) {
      await this.popup.add(ConfirmPopup, {
        title: _t("Invoice required"),
        body: _t(
          "An invoice must be set for every order. Please enable invoicing for this order before paying."
        ),
      });
      return false;
    }
    return super._isOrderValid(isForceValidate);
  },
});

/**
 * Override ProductScreen: require customer before order when
 * pos.config.require_customer === "order", and add discount validation for gold.
 */
patch(ProductScreen.prototype, {
  onMounted() {
    if (
      this.pos.config.require_customer === "order" &&
      !this.pos.get_order().get_partner()
    ) {
      this.pos.showTempScreen("PartnerListScreen", {});
    }
    super.onMounted(...arguments);
  },

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
      const effectiveMin =
        minSalePrice > 0 ? minSalePrice : currentPrice * 0.8;

      if (effectiveMin > 0 && currentPrice > 0) {
        let maxDiscountPercent = 20;
        if (costPrice > 0 && listPrice > 0) {
          const markupTotal = listPrice - costPrice;
          maxDiscountPercent =
            ((markupTotal * 0.5) / listPrice) * 100;
        }
        const maxDiscountForMinPrice =
          ((currentPrice - effectiveMin) / currentPrice) * 100;
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
