from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auto_invoice_direct_delivery = fields.Boolean(
        string="Auto-Create Draft Customer Invoice on Direct Delivery Validation",
        config_parameter="praswi_delivery_to_invoice_no_so.auto_invoice_direct_delivery",
        help="Automatically create a Draft Customer Invoice when an outgoing Delivery without a Sales Order is validated. Taxes and Fiscal Position are applied natively on the Draft Invoice.",
    )
