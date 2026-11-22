from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    is_direct_delivery_move = fields.Boolean(
        related="picking_id.is_direct_delivery",
        string="Is Direct Delivery Move",
    )
    sale_currency_id = fields.Many2one(
        related="picking_id.sale_currency_id",
        string="Sale Currency",
    )
    sale_unit_price = fields.Float(
        string="Sale Price",
        digits="Product Price",
        copy=True,
        help="Unit sale price transferred to the Draft Customer Invoice.",
    )
    sale_price_subtotal = fields.Monetary(
        string="Sale Subtotal",
        currency_field="sale_currency_id",
        compute="_compute_sale_subtotal",
        store=True,
    )
    delivery_invoice_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="delivery_move_id",
        string="Customer Invoice Lines",
        readonly=True,
    )
    delivery_invoiced_qty = fields.Float(
        string="Invoiced Qty",
        digits="Product Unit of Measure",
        compute="_compute_delivery_invoiced_qty",
        store=True,
    )
    delivery_qty_to_invoice = fields.Float(
        string="Qty to Invoice",
        digits="Product Unit of Measure",
        compute="_compute_delivery_invoiced_qty",
        store=True,
    )

    def _get_sale_effective_qty(self):
        self.ensure_one()
        if self.state == "done" or self.quantity > 0:
            return self.quantity
        return self.product_uom_qty

    @api.depends("is_direct_delivery_move", "quantity", "product_uom_qty", "state", "sale_unit_price")
    def _compute_sale_subtotal(self):
        for move in self:
            if not move.is_direct_delivery_move or not move.product_id:
                move.sale_price_subtotal = 0.0
                continue
            move.sale_price_subtotal = move._get_sale_effective_qty() * move.sale_unit_price

    @api.depends(
        "quantity",
        "state",
        "delivery_invoice_line_ids.quantity",
        "delivery_invoice_line_ids.move_id.state",
    )
    def _compute_delivery_invoiced_qty(self):
        for move in self:
            valid_lines = move.delivery_invoice_line_ids.filtered(
                lambda l: l.move_id.state != "cancel" and l.move_id.move_type == "out_invoice"
            )
            invoiced = sum(valid_lines.mapped("quantity"))
            move.delivery_invoiced_qty = invoiced
            move.delivery_qty_to_invoice = max(0.0, move.quantity - invoiced) if move.state == "done" else 0.0

    def _get_default_sale_price(self):
        self.ensure_one()
        product = self.product_id
        if not product:
            return 0.0

        company = self.company_id or self.env.company
        partner = self.picking_id.partner_id
        currency = self.picking_id.sale_currency_id or company.currency_id

        unit_price = product.with_company(company).lst_price
        pricelist = getattr(partner, "property_product_pricelist", False) if partner else False
        if pricelist and hasattr(pricelist, "_get_product_price"):
            qty = self._get_sale_effective_qty() or 1.0
            unit_price = pricelist._get_product_price(product, qty, uom=(self.uom_id if 'uom_id' in self._fields and self.uom_id else self.product_id.uom_id))
            if pricelist.currency_id and pricelist.currency_id != currency:
                unit_price = pricelist.currency_id._convert(
                    unit_price, currency, company, fields.Date.context_today(self)
                )
        return unit_price

    @api.onchange("product_id")
    def _onchange_product_id_sale_price(self):
        for move in self:
            if move.picking_id and move.picking_id.is_direct_delivery and move.product_id:
                move.sale_unit_price = move._get_default_sale_price()

    def _prepare_delivery_customer_invoice_line(self):
        """Prepare invoice line without forcing tax_ids so Odoo natively applies Fiscal Position & Taxes."""
        self.ensure_one()
        return {
            "product_id": self.product_id.id,
            "name": self.description_picking or self.product_id.display_name,
            "quantity": self.delivery_qty_to_invoice,
            "product_uom_id": (self.uom_id.id if "uom_id" in self._fields and self.uom_id else self.product_id.uom_id.id),
            "price_unit": self.sale_unit_price,
            "delivery_move_id": self.id,
        }
