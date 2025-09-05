# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging
from collections import defaultdict as default_dict
from datetime import datetime
from dateutil.relativedelta import relativedelta


_logger = logging.getLogger(__name__)


class StockLocation(models.Model):
    _inherit = 'stock.location'

    url_download = fields.Char(string='Stock Rapport Téléchargment', compute='_compute_url', store=True)

    def _compute_url(self):
        for stock in self:
            if stock:
                stock.url_download = f'https://diffusion-nord-sud.be/rapport_stock/{stock.id}'
            else:
                stock.url_download = None


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    sale_id = fields.Many2one('sale.order', string="Sale Order")


class StockWarehouseOrderpointinfo(models.Model):
    _name = 'stock.warehouse.orderpointinfo'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    order_id = fields.Many2one('sale.order', string="Sale Order", readonly=True)
    qty = fields.Float(string="Quantity", readonly=True)

    @api.depends('order_id', 'qty')
    def _compute_name(self):
        for rec in self:
            if rec.order_id:
                rec.name = rec.order_id.name + '-' + rec.order_id.partner_id.name
                rec.name += f' ({int(rec.qty)})' if rec.qty else ' (0)'


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    orderpont_info_ids = fields.Many2many(
        'stock.warehouse.orderpointinfo',
        'stock_orderpoint_info_rel',
        'orderpoint_id',
        'info_id',
        string="Order Point Info",
        readonly=True, store=True, ondelete='cascade'
    )
    partner_ids = fields.Many2many(
        'res.partner',  # Target model
        'stock_orderpoint_partner_rel',  # Relation table name
        'orderpoint_id',  # Column for the current model
        'partner_id',  # Column for the target model
        string="Client Names",
        store=True
    )
    supplier2_id = fields.Many2one('res.partner', string="Supplier")
    vendor2_id = fields.Many2one('res.partner', string="Vendor", )

    @api.model
    def cron_generate_manual_orderpoints_warehouse_1(self, offset=0, limit=1000):
        """Optimized cron to generate manual orderpoints only for warehouse ID 1, with batching via offset/limit."""
        warehouse_id = 1
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        today = fields.Datetime.now().replace(hour=23, minute=59, second=59)
        lead_days = 2  # fixed to avoid _get_lead_days memory issue

        # Hardcoded single location for now
        replenish_locations = list(self.env['stock.location'].browse(8))
        _logger.info(f"[REPLENISH] Processing location(s): {replenish_locations}")

        if not replenish_locations:
            _logger.info("[REPLENISH] No replenish locations found for warehouse ID 1.")
            return

        # Domain: active stockable products
        product_domain = [
            ('type', '=', 'product'),
            ('active', '=', True),
        ]

        products = self.env['product.product'].search(product_domain, offset=offset, limit=limit)
        _logger.info(f"[REPLENISH] Processing products {offset} to {offset + len(products)}")

        if not products:
            _logger.info("[REPLENISH] No products found for this offset/limit batch.")
            return

        to_refill = default_dict(float)

        for loc in replenish_locations:
            loc_id = loc.id
            product_qties = products.with_context(
                location=loc_id,
                to_date=today + relativedelta(days=lead_days)
            ).read(['id', 'virtual_available', 'uom_id'])

            for pq in product_qties:
                product_uom = self.env['uom.uom'].browse(pq['uom_id'][0])
                virtual_qty = pq['virtual_available']
                if float_compare(virtual_qty, 0, precision_rounding=product_uom.rounding) < 0:
                    to_refill[(pq['id'], loc_id)] = virtual_qty

        if not to_refill:
            _logger.info("[REPLENISH] No products to replenish for this batch.")
            return

        product_ids, location_ids = zip(*to_refill.keys())
        qty_in_progress, _ = self.env['product.product'].browse(product_ids)._get_quantity_in_progress(
            location_ids=location_ids)

        existing_orderpoints = self.env['stock.warehouse.orderpoint'].with_context(active_test=False).search([
            ('product_id', 'in', product_ids),
            ('location_id', 'in', location_ids),
        ])
        existing_op_map = {(op.product_id.id, op.location_id.id): op for op in existing_orderpoints}

        orderpoints_to_create = []

        for (product_id, loc_id), forecast_qty in to_refill.items():
            total_needed = forecast_qty + qty_in_progress.get((product_id, loc_id), 0.0)

            if float_compare(total_needed, 0.0, precision_digits=rounding) < 0:
                op = existing_op_map.get((product_id, loc_id))
                if op and op.trigger == 'manual':
                    op.qty_forecast += total_needed
                else:
                    location = self.env['stock.location'].browse(loc_id)
                    orderpoints_to_create.append({
                        'name': 'Replenishment Report',
                        'trigger': 'manual',
                        'product_id': product_id,
                        'location_id': loc_id,
                        'company_id': location.company_id.id,
                        'warehouse_id': warehouse_id,
                        'product_min_qty': 0.0,
                        'product_max_qty': 0.0,
                    })

        if orderpoints_to_create:
            new_ops = self.env['stock.warehouse.orderpoint'].with_user(SUPERUSER_ID).create(orderpoints_to_create)
            for op in new_ops:
                op._set_default_route_id()
                op.qty_multiple = op._get_qty_multiple_to_order()

        self._unlink_processed_orderpoints()
