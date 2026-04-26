from odoo import api, fields, models


class StockStorageCost(models.Model):
    _name = 'stock.storage.cost'
    _description = 'Daily Storage Cost Log'
    _order = 'date desc, id desc'
    _rec_name = 'date'

    STORAGE_COST_RATE = 0.01  # USD per kg per day

    date = fields.Date(required=True, index=True)
    product_id = fields.Many2one('product.product', required=True, index=True)
    lot_id = fields.Many2one('stock.lot')
    source_layer_id = fields.Many2one(
        'stock.valuation.layer', string='Source Layer', ondelete='set null', index=True
    )
    adjustment_layer_id = fields.Many2one(
        'stock.valuation.layer', string='Adjustment Layer', ondelete='set null'
    )
    quantity_kg = fields.Float('Qty (kg)', digits=(16, 2))
    storage_cost = fields.Float('Storage Cost (USD)', digits=(16, 2))
    initial_unit_cost = fields.Float('Initial Unit Cost', digits=(16, 2))
    adjustment_number = fields.Integer('Adjustment #')

    @api.model
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

        if not layers:
            return

        # Pre-compute adjustment counts to avoid N+1 queries
        existing_counts = self.read_group(
            domain=[('source_layer_id', 'in', layers.ids)],
            fields=['source_layer_id'],
            groupby=['source_layer_id'],
        )
        counts_by_layer = {
            row['source_layer_id'][0]: row['source_layer_id_count']
            for row in existing_counts
        }

        logs = []
        adj_layers_vals = []

        for layer in layers:
            product = layer.product_id
            uom = product.uom_id

            if uom.category_id == kg_uom.category_id:
                qty_kg = uom._compute_quantity(layer.remaining_qty, kg_uom)
            else:
                qty_kg = layer.remaining_qty * product.weight

            if qty_kg <= 0.0:
                continue

            storage_cost = qty_kg * self.STORAGE_COST_RATE
            adj_number = counts_by_layer.get(layer.id, 0) + 1

            lot_id = False
            if layer.stock_move_id:
                move_line = layer.stock_move_id.move_line_ids[:1]
                lot_id = move_line.lot_id.id if move_line else False

            adj_layers_vals.append({
                'layer': layer,
                'product_id': product.id,
                'storage_cost': storage_cost,
                'adj_number': adj_number,
                'qty_kg': qty_kg,
                'lot_id': lot_id,
            })

        for vals in adj_layers_vals:
            layer = vals['layer']
            adj_layer = self.env['stock.valuation.layer'].create({
                'product_id': vals['product_id'],
                'quantity': 0.0,
                'value': vals['storage_cost'],
                'description': f'Daily storage cost #{vals["adj_number"]} — {today}',
                'company_id': layer.company_id.id,
            })

            logs.append({
                'date': today,
                'product_id': vals['product_id'],
                'lot_id': vals['lot_id'],
                'source_layer_id': layer.id,
                'adjustment_layer_id': adj_layer.id,
                'quantity_kg': vals['qty_kg'],
                'storage_cost': vals['storage_cost'],
                'initial_unit_cost': layer.unit_cost,
                'adjustment_number': vals['adj_number'],
            })

        if logs:
            self.create(logs)


class StockStorageCostReport(models.Model):
    _name = 'stock.storage.cost.report'
    _description = 'Storage Cost Analysis'
    _auto = False

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot', readonly=True)
    initial_unit_cost = fields.Float('Initial Unit Cost', digits=(16, 2), readonly=True)
    adjustment_count = fields.Integer('Adjustments #', readonly=True)
    total_storage_cost = fields.Float('Total Storage Cost', digits=(16, 2), readonly=True)
    current_unit_cost = fields.Float('Current Unit Cost', digits=(16, 2), readonly=True)

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
