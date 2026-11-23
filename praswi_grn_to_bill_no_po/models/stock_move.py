from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    is_direct_grn_move = fields.Boolean(
        related="picking_id.is_direct_grn",
        string="Is Direct Receipt Move",
    )
    purchase_currency_id = fields.Many2one(
        related="picking_id.purchase_currency_id",
        string="Purchase Currency",
    )
    purchase_unit_price = fields.Float(
        string="Purchase Cost",
        digits="Product Price",
        copy=True,
        help="Unit purchase cost transferred to the Draft Vendor Bill.",
    )
    purchase_price_subtotal = fields.Monetary(
        string="Purchase Subtotal",
        currency_field="purchase_currency_id",
        compute="_compute_purchase_subtotal",
        store=True,
    )
    grn_bill_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="grn_move_id",
        string="Vendor Bill Lines",
        readonly=True,
    )
    grn_billed_qty = fields.Float(
        string="Billed Qty",
        digits="Product Unit of Measure",
        compute="_compute_grn_billed_qty",
        store=True,
    )
    grn_qty_to_bill = fields.Float(
        string="Qty to Bill",
        digits="Product Unit of Measure",
        compute="_compute_grn_billed_qty",
        store=True,
    )

    def _get_purchase_effective_qty(self):
        self.ensure_one()
        if self.state == "done" or self.quantity > 0:
            return self.quantity
        return self.product_uom_qty

    @api.depends("is_direct_grn_move", "quantity", "product_uom_qty", "state", "purchase_unit_price")
    def _compute_purchase_subtotal(self):
        for move in self:
            if not move.is_direct_grn_move or not move.product_id:
                move.purchase_price_subtotal = 0.0
                continue
            move.purchase_price_subtotal = move._get_purchase_effective_qty() * move.purchase_unit_price

    @api.depends("quantity", "state", "grn_bill_line_ids.quantity", "grn_bill_line_ids.move_id.state")
    def _compute_grn_billed_qty(self):
        for move in self:
            valid_lines = move.grn_bill_line_ids.filtered(
                lambda l: l.move_id.state != "cancel" and l.move_id.move_type == "in_invoice"
            )
            billed = sum(valid_lines.mapped("quantity"))
            move.grn_billed_qty = billed
            move.grn_qty_to_bill = max(0.0, move.quantity - billed) if move.state == "done" else 0.0

    def _get_default_purchase_cost(self):
        self.ensure_one()
        product = self.product_id
        if not product:
            return 0.0

        company = self.company_id or self.env.company
        partner = self.picking_id.partner_id
        currency = self.picking_id.purchase_currency_id or company.currency_id

        unit_price = product.with_company(company).standard_price
        if partner and "seller_ids" in product._fields:
            qty = self._get_purchase_effective_qty() or 1.0
            sellers = product.seller_ids.filtered(
                lambda s: s.partner_id == partner
                and (not s.company_id or s.company_id == company)
                and s.min_qty <= qty
            )
            if sellers:
                seller = sellers.sorted(key=lambda s: (s.sequence, s.min_qty))[0]
                price = seller.price
                if seller.currency_id and seller.currency_id != currency:
                    price = seller.currency_id._convert(
                        price, currency, company, fields.Date.context_today(self)
                    )
                unit_price = price
        return unit_price

    @api.onchange("product_id")
    def _onchange_product_id_purchase_cost(self):
        for move in self:
            if move.picking_id and move.picking_id.is_direct_grn and move.product_id:
                move.purchase_unit_price = move._get_default_purchase_cost()

    def _get_grn_interim_account(self):
        """Return Stock Interim (Received) account only for real-time valuation; else let Odoo compute."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        categ = product.categ_id.with_company(self.company_id)
        if getattr(categ, "property_valuation", False) == "real_time":
            interim_in = getattr(categ, "property_stock_account_input_categ_id", False)
            if interim_in:
                return interim_in
        return False

    def _prepare_grn_vendor_bill_line(self):
        """Prepare bill line without forcing tax_ids so Odoo natively applies Fiscal Position & Taxes."""
        self.ensure_one()
        vals = {
            "product_id": self.product_id.id,
            "name": self.description_picking or self.product_id.display_name,
            "quantity": self.grn_qty_to_bill,
            "product_uom_id": (self.uom_id.id if "uom_id" in self._fields and self.uom_id else self.product_id.uom_id.id),
            "price_unit": self.purchase_unit_price,
            "grn_move_id": self.id,
        }
        interim_account = self._get_grn_interim_account()
        if interim_account:
            vals["account_id"] = interim_account.id
        return vals
