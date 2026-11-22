from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    require_gate_pass_on_grn = fields.Boolean(
        string="Require Inward Gate Pass before GRN Validation",
        config_parameter="praswi_grn_gate_pass.require_gate_pass_on_grn",
        help="Block validating incoming Receipts (GRN) unless Vehicle Number and Supplier Challan/Invoice Number are recorded.",
    )
