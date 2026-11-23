{
    "name": "Direct GRN to Draft Vendor Bill (Without PO)",
    "version": "20.0.1.1.3",
    "category": "Inventory/Accounting",
    "summary": "Purchase Cost on Receipts (GRN) and Draft Vendor Bill creation without PO—letting native Odoo handle Taxes and Fiscal Position on the Bill.",
    "description": """
Direct GRN to Draft Vendor Bill (Without PO)
============================================
Records Purchase Cost on Incoming Receipts (GRN) without a Purchase Order and
creates Draft Vendor Bills where Odoo's native Accounting engine automatically
applies Fiscal Position and Purchase Taxes.

Key Features:
- Auto-populates Purchase Cost (vendor pricelist / standard cost) and line subtotal on Direct Receipts.
- Always creates Vendor Bills in Draft so Fiscal Position and Taxes compute natively on the Bill.
- Optional Auto-Create Draft Vendor Bill on Receipt Validation.
- One-click Create Vendor Bill + Multi-GRN Consolidation from the Receipts list view.
- Two-way smart buttons & strict duplicate-billing guard (To Bill / Partially Billed / Fully Billed).
- Automated Inventory Valuation (Stock Interim - Received) account support.
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
