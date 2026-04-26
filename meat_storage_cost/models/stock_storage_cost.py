from odoo import fields, models


class StockStorageCost(models.Model):
    _name = 'stock.storage.cost'
    _description = 'Daily Storage Cost Log'
    _order = 'date desc, id desc'

    date = fields.Date(required=True)
    product_id = fields.Many2one('product.product', required=True, index=True)
    lot_id = fields.Many2one('stock.lot')
    source_layer_id = fields.Many2one('stock.valuation.layer', string='Source Layer')
    adjustment_layer_id = fields.Many2one('stock.valuation.layer', string='Adjustment Layer')
    quantity_kg = fields.Float('Qty (kg)', digits=(16, 4))
    storage_cost = fields.Float('Storage Cost (USD)', digits=(16, 4))
    initial_unit_cost = fields.Float('Initial Unit Cost', digits=(16, 4))
    adjustment_number = fields.Integer('Adjustment #')

    def _compute_daily_storage_costs(self):
        today = fields.Date.today()

        if self.search([('date', '=', today)], limit=1):
            return

        kg_uom = self.env.ref('uom.product_uom_kgm')

        layers = self.env['stock.valuation.layer'].search([
            ('remaining_qty', '>', 0.0),
            ('quantity', '>', 0.0),
            ('product_id.categ_id.property_cost_method', '=', 'fifo'),
        ])

        for layer in layers:
            product = layer.product_id
            uom = product.uom_id

            if uom.category_id == kg_uom.category_id:
                qty_kg = uom._compute_quantity(layer.remaining_qty, kg_uom)
            else:
                qty_kg = layer.remaining_qty * product.weight

            if qty_kg <= 0.0:
                continue

            storage_cost = qty_kg * 0.01

            adj_number = self.search_count([('source_layer_id', '=', layer.id)]) + 1

            adj_layer = self.env['stock.valuation.layer'].create({
                'product_id': product.id,
                'quantity': 0.0,
                'unit_cost': 0.0,
                'value': storage_cost,
                'remaining_qty': 0.0,
                'remaining_value': 0.0,
                'description': f'Daily storage cost #{adj_number} — {today}',
                'company_id': layer.company_id.id,
            })

            lot_id = False
            if layer.stock_move_id:
                move_line = layer.stock_move_id.move_line_ids[:1]
                lot_id = move_line.lot_id.id if move_line else False

            self.create({
                'date': today,
                'product_id': product.id,
                'lot_id': lot_id,
                'source_layer_id': layer.id,
                'adjustment_layer_id': adj_layer.id,
                'quantity_kg': qty_kg,
                'storage_cost': storage_cost,
                'initial_unit_cost': layer.unit_cost,
                'adjustment_number': adj_number,
            })


class StockStorageCostReport(models.Model):
    _name = 'stock.storage.cost.report'
    _description = 'Storage Cost Analysis'
    _auto = False

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot', readonly=True)
    initial_unit_cost = fields.Float('Initial Unit Cost', digits=(16, 4), readonly=True)
    adjustment_count = fields.Integer('Adjustments #', readonly=True)
    total_storage_cost = fields.Float('Total Storage Cost', digits=(16, 4), readonly=True)
    current_unit_cost = fields.Float('Current Unit Cost', digits=(16, 4), readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW stock_storage_cost_report AS (
                SELECT
                    row_number() OVER ()            AS id,
                    ssc.product_id,
                    ssc.lot_id,
                    svl.unit_cost                   AS initial_unit_cost,
                    COUNT(ssc.id)                   AS adjustment_count,
                    SUM(ssc.storage_cost)           AS total_storage_cost,
                    svl.unit_cost + SUM(ssc.storage_cost) / NULLIF(svl.quantity, 0)
                                                    AS current_unit_cost
                FROM stock_storage_cost ssc
                JOIN stock_valuation_layer svl ON svl.id = ssc.source_layer_id
                GROUP BY ssc.product_id, ssc.lot_id, svl.unit_cost, svl.quantity
            )
        """)
