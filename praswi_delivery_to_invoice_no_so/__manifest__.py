{
    "name": "Direct Delivery to Draft Customer Invoice (Without SO)",
    "version": "20.0.1.1.0",
    "category": "Inventory/Accounting",
    "summary": "Sale Price on Deliveries and Draft Customer Invoice creation without SO—letting native Odoo handle Taxes and Fiscal Position on the Invoice.",
    "description": """
Direct Delivery to Draft Customer Invoice (Without SO)
======================================================
Records Sale Price on Outgoing Deliveries without a Sales Order and creates
Draft Customer Invoices where Odoo's native Accounting engine automatically
applies Fiscal Position and Sales Taxes.

Key Features:
- Auto-populates Sale Price (customer pricelist / product list price) and line subtotal on Direct Deliveries.
- Always creates Customer Invoices in Draft so Fiscal Position and Taxes compute natively on the Invoice.
- Optional Auto-Create Draft Customer Invoice on Delivery Validation.
- One-click Create Draft Invoice + Multi-Delivery Consolidation from the Deliveries list view.
- Two-way smart buttons & strict duplicate-invoicing guard (To Invoice / Partially Invoiced / Fully Invoiced).
- 100% standalone (depends only on stock and account; compatible with Community & Enterprise).
    """,
    "author": "Praswi Technologies",
    "website": "https://www.praswi.com",
    "license": "LGPL-3",
    "depends": ["stock", "account"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/stock_picking_views.xml",
        "views/account_move_views.xml",
    ],
    "support": "nitesh@praswi.com",
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
