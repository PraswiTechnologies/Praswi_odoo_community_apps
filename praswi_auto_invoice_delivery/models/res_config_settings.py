from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auto_create_invoice_on_delivery = fields.Boolean(
        string="Auto-Create Invoice on SO Delivery Validation",
        config_parameter="praswi_auto_invoice_delivery.auto_create_invoice_on_delivery",
        help="Automatically create a Customer Invoice from the linked Sales Order when an outgoing Delivery Order is validated.",
    )
    auto_post_so_delivery_invoice = fields.Boolean(
        string="Auto-Post Created Invoice",
        config_parameter="praswi_auto_invoice_delivery.auto_post_so_delivery_invoice",
        help="Automatically post the Customer Invoice after creation. Leave unchecked to keep invoices in Draft for Accounts review.",
    )
