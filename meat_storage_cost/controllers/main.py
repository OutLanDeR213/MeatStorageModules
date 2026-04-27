import json
import logging

from odoo import http, fields
from odoo.http import request, Response


_logger = logging.getLogger(__name__)


class StorageCostAPI(http.Controller):

    # ── helpers ──────────────────────────────────────────────────────────────

    def _json_response(self, data, status=200):
        return Response(
            json.dumps(data),
            status=status,
            mimetype='application/json',
        )

    def _error(self, message, status=400):
        return self._json_response({'success': False, 'error': message}, status)

    # ── endpoints ─────────────────────────────────────────────────────────────

    @http.route(
        '/api/v1/storage-costs',
        type='http', auth='api_key', methods=['GET'], csrf=False,
    )
    def list_storage_costs(self, limit='50', offset='0', product_id=None):
        """
        List daily storage cost accruals.

        Query params:
            limit      (int, default 50)
            offset     (int, default 0)
            product_id (int, optional) — filter by product
        """
        try:
            limit = int(limit)
            offset = int(offset)
        except ValueError:
            return self._error('limit and offset must be integers')

        try:
            domain = []
            if product_id:
                domain.append(('product_id', '=', int(product_id)))

            model = request.env['stock.storage.cost']
            records = model.search(domain, limit=limit, offset=offset, order='date desc')
            total = model.search_count(domain)

            data = [
                {
                    'id': r.id,
                    'date': str(r.date),
                    'product': r.product_id.display_name,
                    'lot': r.lot_id.name or None,
                    'quantity_kg': r.quantity_kg,
                    'storage_cost': r.storage_cost,
                    'initial_unit_cost': r.initial_unit_cost,
                    'adjustment_number': r.adjustment_number,
                }
                for r in records
            ]

            return self._json_response({
                'success': True,
                'total': total,
                'limit': limit,
                'offset': offset,
                'data': data,
            })

        except Exception:
            _logger.exception('GET /api/v1/storage-costs failed')
            return self._error('Internal server error', status=500)

    @http.route(
        '/api/v1/storage-costs/report',
        type='http', auth='api_key', methods=['GET'], csrf=False,
    )
    def get_report(self):
        """
        Return aggregated storage cost report grouped by product and lot.
        Shows initial cost, number of accruals, and current unit cost.
        """
        try:
            records = request.env['stock.storage.cost.report'].search([])

            data = [
                {
                    'product': r.product_id.display_name,
                    'lot': r.lot_id.name or None,
                    'initial_unit_cost': r.initial_unit_cost,
                    'adjustment_count': r.adjustment_count,
                    'total_storage_cost': r.total_storage_cost,
                    'current_unit_cost': r.current_unit_cost,
                }
                for r in records
            ]

            return self._json_response({'success': True, 'data': data})

        except Exception:
            _logger.exception('GET /api/v1/storage-costs/report failed')
            return self._error('Internal server error', status=500)

    @http.route(
        '/api/v1/storage-costs/run',
        type='http', auth='api_key', methods=['POST'], csrf=False,
    )
    def run_accrual(self):
        """
        Manually trigger the daily storage cost accrual.
        Idempotent: if accrual already ran today, returns a notice without re-running.
        """
        try:
            today = fields.Date.today()
            already_ran = request.env['stock.storage.cost'].search_count(
                [('date', '=', today)]
            )

            if already_ran:
                return self._json_response({
                    'success': True,
                    'message': f'Accrual already ran today ({today}), skipped.',
                })

            request.env['stock.storage.cost']._compute_daily_storage_costs()

            return self._json_response({
                'success': True,
                'message': f'Accrual completed for {today}.',
            })

        except Exception:
            _logger.exception('POST /api/v1/storage-costs/run failed')
            return self._error('Internal server error', status=500)
