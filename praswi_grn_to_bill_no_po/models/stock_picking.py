from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_direct_grn = fields.Boolean(
        string="Is Direct Receipt (No PO)",
        compute="_compute_is_direct_grn",
        store=True,
    )
    purchase_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Purchase Currency",
        default=lambda self: self.env.company.currency_id,
    )
    purchase_amount_total = fields.Monetary(
        string="Total Purchase Cost",
        currency_field="purchase_currency_id",
        compute="_compute_purchase_amount_total",
        store=True,
    )
    grn_bill_ids = fields.Many2many(
        comodel_name="account.move",
        relation="praswi_grn_picking_account_move_rel",
        column1="picking_id",
        column2="move_id",
        string="Vendor Bills",
        copy=False,
        readonly=True,
    )
    grn_bill_count = fields.Integer(
        string="Vendor Bill Count",
        compute="_compute_grn_billing_info",
    )
    grn_billing_status = fields.Selection(
        selection=[
            ("to_bill", "To Bill"),
            ("partial", "Partially Billed"),
            ("billed", "Fully Billed"),
        ],
        string="Billing Status",
        compute="_compute_grn_billing_info",
        store=True,
    )

    def _has_linked_purchase_order(self):
        self.ensure_one()
        if getattr(self, "purchase_id", False):
            return True
        for move in self.move_ids:
            if getattr(move, "purchase_line_id", False):
                return True
        return False

    @api.depends("picking_type_id", "picking_type_code", "return_id", "move_ids")
    def _compute_is_direct_grn(self):
        for picking in self:
            is_incoming = picking.picking_type_code == "incoming"
            is_return = bool(getattr(picking, "return_id", False))
            has_po = picking._has_linked_purchase_order()
            picking.is_direct_grn = is_incoming and not is_return and not has_po

    @api.depends("is_direct_grn", "move_ids.purchase_price_subtotal", "move_ids.state")
    def _compute_purchase_amount_total(self):
        for picking in self:
            if not picking.is_direct_grn:
                picking.purchase_amount_total = 0.0
                continue
            moves = picking.move_ids.filtered(lambda m: m.state != "cancel")
            picking.purchase_amount_total = sum(moves.mapped("purchase_price_subtotal"))

    @api.depends(
        "is_direct_grn",
        "state",
        "grn_bill_ids",
        "grn_bill_ids.state",
        "move_ids.quantity",
        "move_ids.grn_billed_qty",
        "move_ids.grn_qty_to_bill",
    )
    def _compute_grn_billing_info(self):
        for picking in self:
            active_bills = picking.grn_bill_ids.filtered(lambda b: b.state != "cancel")
            picking.grn_bill_count = len(active_bills)
            if not picking.is_direct_grn or picking.state != "done":
                picking.grn_billing_status = False
                continue
            done_moves = picking.move_ids.filtered(lambda m: m.state == "done" and m.quantity > 0)
            total_qty = sum(done_moves.mapped("quantity"))
            billed_qty = sum(done_moves.mapped("grn_billed_qty"))
            if total_qty <= 0 or billed_qty <= 0:
                picking.grn_billing_status = "to_bill"
            elif billed_qty < total_qty:
                picking.grn_billing_status = "partial"
            else:
                picking.grn_billing_status = "billed"

    @api.onchange("partner_id", "picking_type_id")
    def _onchange_partner_purchase_cost_defaults(self):
        for picking in self:
            if not picking.is_direct_grn:
                continue
            if not picking.purchase_currency_id:
                picking.purchase_currency_id = picking.company_id.currency_id or self.env.company.currency_id
            if picking.partner_id:
                for move in picking.move_ids:
                    if move.product_id and not move.purchase_unit_price:
                        move.purchase_unit_price = move._get_default_purchase_cost()

    def _create_direct_grn_draft_bill(self):
        pickings = self.filtered(lambda p: p.is_direct_grn and p.state == "done")
        if not pickings:
            raise UserError(_("Please select at least one validated Direct Receipt (without PO)."))

        partners = pickings.mapped("partner_id")
        if not partners or len(partners) > 1:
            raise UserError(_("All selected Receipts must belong to the same Vendor."))

        companies = pickings.mapped("company_id")
        if len(companies) > 1:
            raise UserError(_("All selected Receipts must belong to the same Company."))

        currencies = pickings.mapped("purchase_currency_id")
        if len(currencies) > 1:
            raise UserError(_("All selected Receipts must use the same Purchase Currency."))

        partner = partners[0]
        company = companies[0]
        currency = currencies[0] if currencies else company.currency_id

        invoice_lines = []
        used_pickings = self.env["stock.picking"]
        for picking in pickings:
            billable_moves = picking.move_ids.filtered(
                lambda m: m.state == "done" and m.grn_qty_to_bill > 0
            )
            for move in billable_moves:
                invoice_lines.append((0, 0, move._prepare_grn_vendor_bill_line()))
            if billable_moves:
                used_pickings |= picking

        if not invoice_lines:
            raise UserError(_("All received quantities on the selected Receipt(s) have already been billed."))

        journal = self.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", company.id)], limit=1
        )
        if not journal:
            raise UserError(_("No Purchase Journal found for company %s.") % company.display_name)

        # Do NOT force fiscal_position_id or tax_ids: Odoo computes them natively on the Draft Bill.
        bill_vals = {
            "move_type": "in_invoice",
            "partner_id": partner.id,
            "company_id": company.id,
            "journal_id": journal.id,
            "currency_id": currency.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_origin": ", ".join(used_pickings.mapped("name")),
            "grn_picking_ids": [(6, 0, used_pickings.ids)],
            "invoice_line_ids": invoice_lines,
        }
        return self.env["account.move"].with_company(company).create(bill_vals)

    def action_create_grn_vendor_bill(self):
        bill = self._create_direct_grn_draft_bill()
        return {
            "name": _("Draft Vendor Bill"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": bill.id,
            "target": "current",
        }

    def action_view_grn_vendor_bills(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
        bills = self.grn_bill_ids.filtered(lambda b: b.state != "cancel")
        if len(bills) == 1:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = bills.id
        else:
            action["domain"] = [("id", "in", bills.ids)]
        return action

    def button_validate(self):
        res = super().button_validate()
        icp = self.env["ir.config_parameter"].sudo()
        auto_bill = icp.get_bool("praswi_grn_to_bill_no_po.auto_bill_direct_grn")
        if auto_bill:
            self.env.flush_all()
            for picking in self.filtered(lambda p: p.is_direct_grn and p.state == "done" and p.partner_id):
                picking.move_ids.invalidate_recordset(["grn_billed_qty", "grn_qty_to_bill"])
                if any(m.grn_qty_to_bill > 0 for m in picking.move_ids if m.state == "done"):
                    picking._create_direct_grn_draft_bill()
        return res
