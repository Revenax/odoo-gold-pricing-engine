/** @odoo-module **/
/**
 * Copyright 2026 Revenax Digital Services
 * Author: Mohamed A. Abdallah
 * Website: https://www.revenax.com
 */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/**
 * When require_customer is enabled on the POS config, block opening the
 * payment screen until a customer is set on the order.
 */
patch(PaymentScreen.prototype, {
  setup() {
    super.setup(...arguments);
    const order = this.pos.get_order();
    if (!order) return;
    if (this.pos.config.require_customer) {
      const partner = order.get_partner
        ? order.get_partner()
        : order.partner_id;
      if (!partner) {
        this.pos.notification.add(
          _t("Please select a customer before payment."),
          { type: "danger" },
        );
        this.pos.navigate_to_previous_screen();
      }
    }
  },
});
