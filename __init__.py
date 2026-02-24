# -*- coding: utf-8 -*-
# Copyright 2026 Revenax Digital Services
# Author: Mohamed A. Abdallah
# Website: https://www.revenax.com

# Only run when loaded as a package (e.g. by Odoo). When the repo root has a
# hyphenated name (e.g. odoo-jewellery-evaluator), pytest may load this file
# without a parent package, which would make "from . import ..." fail.
if __package__:
    from . import jewellery_evaluator  # noqa: F401
