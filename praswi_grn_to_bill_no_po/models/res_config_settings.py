from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auto_bill_direct_grn = fields.Boolean(
        string="Auto-Create Draft Vendor Bill on Direct GRN Validation",
        config_parameter="praswi_grn_to_bill_no_po.auto_bill_direct_grn",
        help="Automatically create a Draft Vendor Bill when an incoming Receipt without a Purchase Order is validated. Taxes and Fiscal Position are applied natively on the Draft Bill.",
    )
