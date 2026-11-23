{
    "name": "Multi-Level BOM Raw Material Calculator",
    "version": "20.0.1.0.3",
    "category": "Manufacturing/Inventory",
    "summary": "Standalone calculator to explode single or multi-level BOMs across multiple products and aggregate total raw material requirements for easy procurement.",
    "description": """
Multi-Level BOM Raw Material Calculator
=======================================
A lightweight, standalone procurement planning calculator for Odoo 20.
Select multiple finished or semi-finished products, pick their Bills of Materials (BOMs)
and target quantities, and instantly calculate the consolidated raw material requirements.

Key Features:
- Multi-Product & Multi-BOM Selection: Combine any number of products and specific BOM versions in one calculation.
- Full Multi-Level BOM Explosion: Recursively drills down through nested sub-assemblies and kits with automatic circular-BOM protection.
- Accurate UoM Conversion: Converts component quantities across different Units of Measure into each raw material's base UoM.
- Procurement-Ready Stock Comparison: Displays Required Qty, On Hand, Forecasted Qty, Shortage (To Procure), Estimated Cost, and which finished products use each raw material.
- Calculator Only (Zero Clutter): Built on TransientModels—does not create draft MOs, POs, or stock moves.
- One-Click CSV (Excel) Export & Printable QWeb PDF Report.
- 100% Standalone (depends only on mrp; compatible with Odoo 20 Community & Enterprise).
    """,
    "author": "Praswi Technologies",
    "website": "https://www.praswi.com",
    "license": "LGPL-3",
    "depends": ["mrp"],
    "data": [
        "security/ir.access.csv",
        "wizard/bom_raw_material_calculator_views.xml",
        "report/bom_calculator_report.xml",
    ],
    "support": "nitesh@praswi.com",
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
