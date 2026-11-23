from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_direct_delivery = fields.Boolean(
        string="Is Direct Delivery (No SO)",
        compute="_compute_is_direct_delivery",
        store=True,
    )
    sale_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Sale Currency",
        default=lambda self: self.env.company.currency_id,
    )
    sale_amount_total = fields.Monetary(
        string="Total Sale Value",
        currency_field="sale_currency_id",
        compute="_compute_sale_amount_total",
        store=True,
    )
    delivery_invoice_ids = fields.Many2many(
        comodel_name="account.move",
        relation="praswi_delivery_picking_account_move_rel",
        column1="picking_id",
        column2="move_id",
        string="Customer Invoices",
        copy=False,
        readonly=True,
    )
    delivery_invoice_count = fields.Integer(
        string="Customer Invoice Count",
        compute="_compute_delivery_invoicing_info",
    )
    delivery_invoicing_status = fields.Selection(
        selection=[
            ("to_invoice", "To Invoice"),
            ("partial", "Partially Invoiced"),
            ("invoiced", "Fully Invoiced"),
        ],
        string="Invoicing Status",
        compute="_compute_delivery_invoicing_info",
        store=True,
    )

    def _has_linked_sale_order(self):
        self.ensure_one()
        if getattr(self, "sale_id", False):
            return True
        for move in self.move_ids:
            if getattr(move, "sale_line_id", False):
                return True
        return False

    @api.depends("picking_type_id", "picking_type_code", "return_id", "move_ids")
    def _compute_is_direct_delivery(self):
        for picking in self:
            is_outgoing = picking.picking_type_code == "outgoing"
            is_return = bool(getattr(picking, "return_id", False))
            has_so = picking._has_linked_sale_order()
            picking.is_direct_delivery = is_outgoing and not is_return and not has_so

    @api.depends("is_direct_delivery", "move_ids.sale_price_subtotal", "move_ids.state")
    def _compute_sale_amount_total(self):
        for picking in self:
            if not picking.is_direct_delivery:
                picking.sale_amount_total = 0.0
                continue
            moves = picking.move_ids.filtered(lambda m: m.state != "cancel")
            picking.sale_amount_total = sum(moves.mapped("sale_price_subtotal"))

    @api.depends(
        "is_direct_delivery",
        "state",
        "delivery_invoice_ids",
        "delivery_invoice_ids.state",
        "move_ids.quantity",
        "move_ids.delivery_invoiced_qty",
        "move_ids.delivery_qty_to_invoice",
    )
    def _compute_delivery_invoicing_info(self):
        for picking in self:
            active_invoices = picking.delivery_invoice_ids.filtered(lambda i: i.state != "cancel")
            picking.delivery_invoice_count = len(active_invoices)
            if not picking.is_direct_delivery or picking.state != "done":
                picking.delivery_invoicing_status = False
                continue
            done_moves = picking.move_ids.filtered(lambda m: m.state == "done" and m.quantity > 0)
            total_qty = sum(done_moves.mapped("quantity"))
            invoiced_qty = sum(done_moves.mapped("delivery_invoiced_qty"))
            if total_qty <= 0 or invoiced_qty <= 0:
                picking.delivery_invoicing_status = "to_invoice"
            elif invoiced_qty < total_qty:
                picking.delivery_invoicing_status = "partial"
            else:
                picking.delivery_invoicing_status = "invoiced"

    @api.onchange("partner_id", "picking_type_id")
    def _onchange_partner_sale_price_defaults(self):
        for picking in self:
            if not picking.is_direct_delivery:
                continue
            company = picking.company_id or self.env.company
            if picking.partner_id:
                pricelist = getattr(picking.partner_id, "property_product_pricelist", False)
                picking.sale_currency_id = (
                    pricelist.currency_id if pricelist and pricelist.currency_id else company.currency_id
                )
                for move in picking.move_ids:
                    if move.product_id and not move.sale_unit_price:
                        move.sale_unit_price = move._get_default_sale_price()
            elif not picking.sale_currency_id:
                picking.sale_currency_id = company.currency_id

    def _create_direct_delivery_draft_invoice(self):
        pickings = self.filtered(lambda p: p.is_direct_delivery and p.state == "done")
        if not pickings:
            raise UserError(_("Please select at least one validated Direct Delivery (without SO)."))

        partners = pickings.mapped("partner_id")
        if not partners or len(partners) > 1:
            raise UserError(_("All selected Deliveries must belong to the same Customer."))

        companies = pickings.mapped("company_id")
        if len(companies) > 1:
            raise UserError(_("All selected Deliveries must belong to the same Company."))

        currencies = pickings.mapped("sale_currency_id")
        if len(currencies) > 1:
            raise UserError(_("All selected Deliveries must use the same Sale Currency."))

        partner = partners[0]
        company = companies[0]
        currency = currencies[0] if currencies else company.currency_id

        invoice_lines = []
        used_pickings = self.env["stock.picking"]
        for picking in pickings:
            invoiceable_moves = picking.move_ids.filtered(
                lambda m: m.state == "done" and m.delivery_qty_to_invoice > 0
            )
            for move in invoiceable_moves:
                invoice_lines.append((0, 0, move._prepare_delivery_customer_invoice_line()))
            if invoiceable_moves:
                used_pickings |= picking

        if not invoice_lines:
            raise UserError(_("All delivered quantities on the selected Delivery(s) have already been invoiced."))

        journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", company.id)], limit=1
        )
        if not journal:
            raise UserError(_("No Sales Journal found for company %s.") % company.display_name)

        # Do NOT force fiscal_position_id or tax_ids: Odoo computes them natively on the Draft Invoice.
        invoice_vals = {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "company_id": company.id,
            "journal_id": journal.id,
            "currency_id": currency.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_origin": ", ".join(used_pickings.mapped("name")),
            "delivery_picking_ids": [(6, 0, used_pickings.ids)],
            "invoice_line_ids": invoice_lines,
        }
        return self.env["account.move"].with_company(company).create(invoice_vals)

    def action_create_delivery_customer_invoice(self):
        invoice = self._create_direct_delivery_draft_invoice()
        return {
            "name": _("Draft Customer Invoice"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": invoice.id,
            "target": "current",
        }

    def action_view_delivery_customer_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        invoices = self.delivery_invoice_ids.filtered(lambda i: i.state != "cancel")
        if len(invoices) == 1:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoices.id
        else:
            action["domain"] = [("id", "in", invoices.ids)]
        return action

    def button_validate(self):
        res = super().button_validate()
        icp = self.env["ir.config_parameter"].sudo()
        auto_inv = icp.get_bool("praswi_delivery_to_invoice_no_so.auto_invoice_direct_delivery")
        if auto_inv:
            self.env.flush_all()
            for picking in self.filtered(lambda p: p.is_direct_delivery and p.state == "done" and p.partner_id):
                picking.move_ids.invalidate_recordset(["delivery_invoiced_qty", "delivery_qty_to_invoice"])
                if any(m.delivery_qty_to_invoice > 0 for m in picking.move_ids if m.state == "done"):
                    picking._create_direct_delivery_draft_invoice()
        return res
