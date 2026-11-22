from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        icp = self.env["ir.config_parameter"].sudo()
        auto_create = icp.get_bool("praswi_auto_invoice_delivery.auto_create_invoice_on_delivery")
        if not auto_create:
            return res

        auto_post = icp.get_bool("praswi_auto_invoice_delivery.auto_post_so_delivery_invoice")
        outgoing_so_pickings = self.filtered(
            lambda p: p.state == "done"
            and p.picking_type_code == "outgoing"
            and not getattr(p, "return_id", False)
            and p.sale_id
            and p.sale_id.state in ("sale", "done")
        )
        if not outgoing_so_pickings:
            return res

        # Flush stock moves so sale.order.line qty_delivered & qty_to_invoice recompute accurately
        self.env.flush_all()
        processed_orders = self.env["sale.order"]
        for picking in outgoing_so_pickings:
            order = picking.sale_id
            if order in processed_orders:
                continue
            processed_orders |= order
            order.order_line.invalidate_recordset(["qty_delivered", "qty_to_invoice", "invoice_status"])
            order.invalidate_recordset(["invoice_status"])
            if order.invoice_status == "to invoice" or any(
                line.qty_to_invoice > 0 for line in order.order_line
            ):
                invoices = order.with_company(order.company_id)._create_invoices()
                if auto_post and invoices:
                    invoices.filtered(lambda inv: inv.state == "draft").action_post()
        return res
