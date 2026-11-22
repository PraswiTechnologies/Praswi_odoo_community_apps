from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    gate_pass_number = fields.Char(
        string="Gate Pass No.",
        copy=False,
        readonly=True,
        index="btree_not_null",
    )
    gate_vehicle_no = fields.Char(string="Vehicle Number", copy=False)
    gate_driver_name = fields.Char(string="Driver Name", copy=False)
    gate_driver_phone = fields.Char(string="Driver Phone", copy=False)
    gate_transporter = fields.Char(string="Transporter", copy=False)
    gate_lr_no = fields.Char(string="LR / Bilty No.", copy=False)
    gate_challan_no = fields.Char(string="Supplier Challan / Invoice No.", copy=False)
    gate_in_time = fields.Datetime(string="Vehicle In-Time", copy=False)
    gate_out_time = fields.Datetime(string="Vehicle Out-Time", copy=False)
    gate_security_officer = fields.Char(string="Security Officer", copy=False)
    gate_remarks = fields.Text(string="Gate / Security Remarks", copy=False)

    def action_generate_gate_pass(self):
        for picking in self:
            if picking.picking_type_code != "incoming":
                continue
            vals = {}
            if not picking.gate_pass_number:
                vals["gate_pass_number"] = self.env["ir.sequence"].next_by_code(
                    "praswi.inward.gate.pass"
                ) or _("New")
            if not picking.gate_in_time:
                vals["gate_in_time"] = fields.Datetime.now()
            if vals:
                picking.write(vals)
        return True

    def action_mark_gate_out_time(self):
        for picking in self:
            if picking.picking_type_code == "incoming":
                picking.gate_out_time = fields.Datetime.now()
        return True

    def button_validate(self):
        icp = self.env["ir.config_parameter"].sudo()
        require_gp = icp.get_bool("praswi_grn_gate_pass.require_gate_pass_on_grn")
        for picking in self.filtered(lambda p: p.picking_type_code == "incoming"):
            if require_gp and (not picking.gate_vehicle_no or not picking.gate_challan_no):
                raise UserError(
                    _(
                        "Inward Gate Pass details are required before validating Receipt %s. "
                        "Please fill at least Vehicle Number and Supplier Challan / Invoice No. under the Gate Pass tab."
                    )
                    % picking.name
                )
            if picking.gate_vehicle_no or picking.gate_challan_no or require_gp:
                picking.action_generate_gate_pass()
        return super().button_validate()
