import csv
import io

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _get_record_uom(record, fallback_product=None):
    """Return UoM safely across Odoo 20 (uom_id) and legacy (product_uom_id) field names."""
    if record:
        if "uom_id" in record._fields and record.uom_id:
            return record.uom_id
        if "product_uom_id" in record._fields and record.product_uom_id:
            return record.product_uom_id
    if fallback_product and fallback_product.uom_id:
        return fallback_product.uom_id
    return False


class BomRawMaterialCalculator(models.TransientModel):
    _name = "bom.raw.material.calculator"
    _description = "Multi-Level BOM Raw Material Calculator"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
    )
    explode_multi_level = fields.Boolean(
        string="Explode Multi-Level BOMs",
        default=True,
        help="Recursively break down sub-assemblies that have their own BOM into base raw materials. Uncheck to see only direct (level-1) components.",
    )
    line_ids = fields.One2many(
        comodel_name="bom.raw.material.calculator.line",
        inverse_name="calculator_id",
        string="Products & BOMs",
    )
    result_ids = fields.One2many(
        comodel_name="bom.raw.material.calculator.result",
        inverse_name="calculator_id",
        string="Total Raw Materials Required",
        readonly=True,
    )
    total_raw_materials = fields.Integer(
        string="Unique Raw Materials",
        compute="_compute_summary",
    )
    total_shortage_items = fields.Integer(
        string="Items in Shortage",
        compute="_compute_summary",
    )
    total_estimated_cost = fields.Monetary(
        string="Total Estimated Cost",
        currency_field="currency_id",
        compute="_compute_summary",
    )

    @api.depends("result_ids.shortage_qty", "result_ids.estimated_cost")
    def _compute_summary(self):
        for rec in self:
            rec.total_raw_materials = len(rec.result_ids)
            rec.total_shortage_items = len(rec.result_ids.filtered(lambda r: r.shortage_qty > 0))
            rec.total_estimated_cost = sum(rec.result_ids.mapped("estimated_cost"))

    def _find_default_bom(self, product):
        self.ensure_one()
        boms_by_product = self.env["mrp.bom"]._bom_find(product, company_id=self.company_id.id)
        return boms_by_product.get(product, self.env["mrp.bom"])

    def _bom_line_applies_to_product(self, bom_line, product):
        """Check variant attribute rules on a BOM line if present."""
        if not product:
            return True
        if hasattr(bom_line, "_skip_bom_line"):
            return not bom_line._skip_bom_line(product)
        return True

    def _explode_bom_recursive(self, bom, product, qty, uom, source_label, raw_totals, visited_boms):
        self.ensure_one()
        if not bom or qty <= 0:
            return

        bom_uom = _get_record_uom(bom, fallback_product=product)
        if uom and bom_uom and uom != bom_uom:
            qty_in_bom_uom = uom._compute_quantity(qty, bom_uom, round=False)
        else:
            qty_in_bom_uom = qty

        base_bom_qty = bom.product_qty or 1.0
        factor = qty_in_bom_uom / base_bom_qty

        for bom_line in bom.bom_line_ids:
            if not self._bom_line_applies_to_product(bom_line, product):
                continue

            comp_product = bom_line.product_id
            if not comp_product:
                continue

            line_qty = bom_line.product_qty * factor
            if line_qty <= 0:
                continue

            line_uom = _get_record_uom(bom_line, fallback_product=comp_product)

            # Check if component has its own sub-BOM
            sub_bom = self._find_default_bom(comp_product)
            should_explode = bool(
                sub_bom
                and sub_bom.id not in visited_boms
                and (self.explode_multi_level or sub_bom.type == "phantom")
            )

            if should_explode:
                self._explode_bom_recursive(
                    bom=sub_bom,
                    product=comp_product,
                    qty=line_qty,
                    uom=line_uom,
                    source_label=source_label,
                    raw_totals=raw_totals,
                    visited_boms=visited_boms | {sub_bom.id},
                )
            else:
                target_uom = comp_product.uom_id
                if line_uom and target_uom and line_uom != target_uom:
                    converted_qty = line_uom._compute_quantity(line_qty, target_uom, round=False)
                else:
                    converted_qty = line_qty

                entry = raw_totals.setdefault(
                    comp_product.id,
                    {"product": comp_product, "qty": 0.0, "sources": set()},
                )
                entry["qty"] += converted_qty
                entry["sources"].add(source_label)

    def action_calculate(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please add at least one Product to calculate raw material requirements."))

        raw_totals = {}
        for line in self.line_ids:
            if line.quantity <= 0:
                raise UserError(
                    _("Quantity must be greater than 0 for product '%s'.") % line.product_id.display_name
                )
            bom = line.bom_id or self._find_default_bom(line.product_id)
            if not bom:
                raise UserError(
                    _("No active Bill of Materials (BOM) found for product '%s'.")
                    % line.product_id.display_name
                )
            line_uom = line.uom_id or _get_record_uom(bom, fallback_product=line.product_id)
            source_label = "%s (x%g)" % (line.product_id.display_name, line.quantity)
            self._explode_bom_recursive(
                bom=bom,
                product=line.product_id,
                qty=line.quantity,
                uom=line_uom,
                source_label=source_label,
                raw_totals=raw_totals,
                visited_boms={bom.id},
            )

        self.result_ids.unlink()
        result_vals_list = []
        sorted_entries = sorted(
            raw_totals.values(),
            key=lambda e: (e["product"].default_code or "", e["product"].name or ""),
        )
        for entry in sorted_entries:
            product = entry["product"].with_company(self.company_id)
            req_qty = entry["qty"]
            on_hand = product.qty_available
            forecasted = product.virtual_available
            shortage_on_hand = max(0.0, req_qty - max(0.0, on_hand))
            shortage_forecast = max(0.0, req_qty - max(0.0, forecasted))
            unit_cost = product.standard_price

            result_vals_list.append(
                {
                    "calculator_id": self.id,
                    "product_id": product.id,
                    "uom_id": product.uom_id.id,
                    "required_qty": req_qty,
                    "qty_available": on_hand,
                    "virtual_available": forecasted,
                    "shortage_qty": shortage_on_hand,
                    "forecast_shortage_qty": shortage_forecast,
                    "unit_cost": unit_cost,
                    "estimated_cost": req_qty * unit_cost,
                    "used_in": ", ".join(sorted(entry["sources"])),
                }
            )

        if result_vals_list:
            self.env["bom.raw.material.calculator.result"].create(result_vals_list)

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_clear(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.result_ids.unlink()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_export_csv(self):
        self.ensure_one()
        if not self.result_ids:
            raise UserError(_("Please click 'Calculate Raw Materials' before exporting."))

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Internal Reference",
                "Raw Material",
                "UoM",
                "Total Required Qty",
                "On Hand Qty",
                "Forecasted Qty",
                "To Procure (vs On Hand)",
                "To Procure (vs Forecast)",
                "Unit Cost",
                "Estimated Cost",
                "Used In Products",
            ]
        )
        for res in self.result_ids:
            writer.writerow(
                [
                    res.default_code or "",
                    res.product_id.display_name,
                    res.uom_id.name or "",
                    round(res.required_qty, 4),
                    round(res.qty_available, 4),
                    round(res.virtual_available, 4),
                    round(res.shortage_qty, 4),
                    round(res.forecast_shortage_qty, 4),
                    round(res.unit_cost, 2),
                    round(res.estimated_cost, 2),
                    res.used_in or "",
                ]
            )

        csv_bytes = ("﻿" + output.getvalue()).encode("utf-8")
        attachment = self.env["ir.attachment"].create(
            {
                "name": "raw_material_requirements.csv",
                "type": "binary",
                "raw": csv_bytes,
                "mimetype": "text/csv",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def action_print_pdf(self):
        self.ensure_one()
        if not self.result_ids:
            raise UserError(_("Please click 'Calculate Raw Materials' before printing."))
        return self.env.ref(
            "praswi_bom_raw_material_calculator.action_report_bom_raw_material_calc"
        ).report_action(self)


class BomRawMaterialCalculatorLine(models.TransientModel):
    _name = "bom.raw.material.calculator.line"
    _description = "BOM Calculator Input Product Line"

    calculator_id = fields.Many2one(
        comodel_name="bom.raw.material.calculator",
        string="Calculator",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
    )
    product_tmpl_id = fields.Many2one(
        related="product_id.product_tmpl_id",
        string="Product Template",
    )
    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Bill of Materials",
        domain="['|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]",
    )
    quantity = fields.Float(
        string="Quantity to Produce",
        digits="Product Unit of Measure",
        default=1.0,
        required=True,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM",
    )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                line.bom_id = False
                line.uom_id = False
                continue
            company_id = line.calculator_id.company_id.id if line.calculator_id else self.env.company.id
            boms = self.env["mrp.bom"]._bom_find(line.product_id, company_id=company_id)
            bom = boms.get(line.product_id, False)
            line.bom_id = bom
            line.uom_id = _get_record_uom(bom, fallback_product=line.product_id)

    @api.onchange("bom_id")
    def _onchange_bom_id(self):
        for line in self:
            if line.bom_id:
                line.uom_id = _get_record_uom(line.bom_id, fallback_product=line.product_id)


class BomRawMaterialCalculatorResult(models.TransientModel):
    _name = "bom.raw.material.calculator.result"
    _description = "BOM Calculator Aggregated Raw Material Result"

    calculator_id = fields.Many2one(
        comodel_name="bom.raw.material.calculator",
        string="Calculator",
        required=True,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(
        related="calculator_id.currency_id",
        string="Currency",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Raw Material",
        readonly=True,
    )
    default_code = fields.Char(
        related="product_id.default_code",
        string="SKU",
        readonly=True,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM",
        readonly=True,
    )
    required_qty = fields.Float(
        string="Total Required",
        digits="Product Unit of Measure",
        readonly=True,
    )
    qty_available = fields.Float(
        string="On Hand",
        digits="Product Unit of Measure",
        readonly=True,
    )
    virtual_available = fields.Float(
        string="Forecasted",
        digits="Product Unit of Measure",
        readonly=True,
    )
    shortage_qty = fields.Float(
        string="To Procure (vs On Hand)",
        digits="Product Unit of Measure",
        readonly=True,
    )
    forecast_shortage_qty = fields.Float(
        string="To Procure (vs Forecast)",
        digits="Product Unit of Measure",
        readonly=True,
    )
    unit_cost = fields.Monetary(
        string="Unit Cost",
        currency_field="currency_id",
        readonly=True,
    )
    estimated_cost = fields.Monetary(
        string="Estimated Cost",
        currency_field="currency_id",
        readonly=True,
    )
    used_in = fields.Char(
        string="Used In Products",
        readonly=True,
    )
