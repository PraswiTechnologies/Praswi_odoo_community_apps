{
    "name": "Inward Gate Pass on GRN (Receipts)",
    "version": "20.0.1.0.1",
    "category": "Inventory/Warehouse",
    "summary": "Sequenced Inward Gate Pass on Receipts (GRN) with Vehicle/Driver/LR/Challan tracking, optional validation lock, and printable PDF.",
    "description": """
Inward Gate Pass on GRN (Receipts)
==================================
Adds complete Security Gate Entry & Inward Gate Pass tracking directly on
Incoming Receipts (GRN) for factories, warehouses, and distributors.

Key Features:
- Auto-sequenced Gate Pass Number (e.g., IGP/2026/0001).
- Dedicated Gate Pass tab on Incoming Receipts: Vehicle No., Driver Name & Phone,
  Transporter, LR/Bilty No., Supplier Challan/Invoice No., In-Time, Out-Time,
  Security Officer, and Remarks.
- Optional Settings toggle: Require Gate Pass before GRN Validation.
- Printable QWeb PDF Inward Gate Pass with Security, Driver, and Store In-Charge signature blocks.
- 100% standalone (depends only on stock; compatible with Odoo 20 Community & Enterprise).
    """,
    "author": "Praswi Technologies",
    "website": "https://www.praswi.com",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "data/ir_sequence_data.xml",
        "views/res_config_settings_views.xml",
        "views/stock_picking_views.xml",
        "report/gate_pass_report.xml",
    ],
    "support": "nitesh@praswi.com",
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
