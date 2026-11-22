from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    grn_picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        relation="praswi_grn_picking_account_move_rel",
        column1="move_id",
        column2="picking_id",
        string="Linked Receipts (GRN)",
        copy=False,
        readonly=True,
    )
    grn_picking_count = fields.Integer(
        string="Receipt Count",
        compute="_compute_grn_picking_count",
    )

    @api.depends("grn_picking_ids")
    def _compute_grn_picking_count(self):
        for move in self:
            move.grn_picking_count = len(move.grn_picking_ids)

    def action_view_grn_pickings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        if len(self.grn_picking_ids) == 1:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = self.grn_picking_ids.id
        else:
            action["domain"] = [("id", "in", self.grn_picking_ids.ids)]
        return action


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    grn_move_id = fields.Many2one(
        comodel_name="stock.move",
        string="Source Receipt Move",
        copy=False,
        index="btree_not_null",
        ondelete="set null",
    )
