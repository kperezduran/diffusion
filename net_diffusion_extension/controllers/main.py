from odoo import http
from odoo.http import request
from collections import defaultdict

class StockMoveReportController(http.Controller):
    # controllers/stock_report.py

    from odoo import http
    from odoo.http import request
    from collections import defaultdict

    class StockMoveReportController(http.Controller):

        @http.route('/custom/stock_report', type='http', auth='user', website=False)
        def stock_report(self, **kwargs):
            StockMove = request.env['stock.move']
            done_moves = StockMove.sudo().search([
                ('state', '=', 'done'),
                ('product_id', '!=', False),
                ('picking_type_id', '!=', False),
            ])

            grouped = defaultdict(lambda: defaultdict(lambda: {
                'product': None, 'supplier': None, 'qty': 0.0
            }))

            # group by (picking_type, warehouse), then by product
            for move in done_moves:
                pt = move.picking_type_id
                wh = pt.warehouse_id
                pid = move.product_id.id
                entry = grouped[(pt, wh)][pid]
                entry['product'] = move.product_id
                entry[
                    'supplier'] = move.created_purchase_line_id.order_id.partner_id if move.created_purchase_line_id else None
                entry['qty'] += move.product_uom_qty

            # Build final structure: list of tuples
            grouped_data = []
            for (pt, wh), prod_map in grouped.items():
                grouped_data.append({
                    'picking_type': pt,
                    'warehouse': wh,
                    'products': list(prod_map.values())
                })

            return request.render('net_diffusion_extension.stock_page_template', {
                'grouped_data': grouped_data,
            })
