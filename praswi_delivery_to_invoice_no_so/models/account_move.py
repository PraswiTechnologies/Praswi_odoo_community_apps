from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    delivery_picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        relation="praswi_delivery_picking_account_move_rel",
        column1="move_id",
        column2="picking_id",
        string="Linked Deliveries",
        copy=False,
        readonly=True,
    )
    delivery_picking_count = fields.Integer(
        string="Delivery Count",
        compute="_compute_delivery_picking_count",
    )

    @api.depends("delivery_picking_ids")
    def _compute_delivery_picking_count(self):
        for move in self:
            move.delivery_picking_count = len(move.delivery_picking_ids)

    def action_view_delivery_pickings(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        if len(self.delivery_picking_ids) == 1:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = self.delivery_picking_ids.id
        else:
            action["domain"] = [("id", "in", self.delivery_picking_ids.ids)]
        return action


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    delivery_move_id = fields.Many2one(
        comodel_name="stock.move",
        string="Source Delivery Move",
        copy=False,
        index="btree_not_null",
        ondelete="set null",
    )
