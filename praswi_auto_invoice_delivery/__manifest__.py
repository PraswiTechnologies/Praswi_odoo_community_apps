{
    "name": "Auto-Invoice on Delivery Validation",
    "version": "20.0.1.0.3",
    "category": "Sales/Inventory",
    "summary": "Automatically create (and optionally post) Customer Invoices when a Sales Order Delivery is validated.",
    "description": """
Auto-Invoice on Delivery Validation
===================================
Eliminates the manual handoff between Warehouse and Accounts by automatically
generating the Customer Invoice as soon as a Delivery Order linked to a Sales Order
is validated.

Key Features:
- Configurable in Inventory Settings: enable Auto-Create Invoice and optional Auto-Post.
- Uses Odoo's native sale.order._create_invoices() so taxes, fiscal positions, and journals stay 100% standard.
- Respects partial deliveries and backorders (only invoices when the Sales Order has invoiceable quantities).
- Safely skips incoming customer returns.
- 100% standalone (compatible with Odoo 20 Community & Enterprise).
    """,
    "author": "Praswi Technologies",
    "website": "https://www.praswi.com",
    "license": "LGPL-3",
    "depends": ["sale_stock", "account"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "support": "nitesh@praswi.com",
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
