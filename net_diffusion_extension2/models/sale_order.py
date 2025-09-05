# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    scan_barcode = fields.Char(string="Scan Barcode")
    scan_quantity = fields.Integer(string="Scan Quantité", default=1, help="Quantity to add when scanning a barcode")

    @api.onchange('scan_barcode')
    def _onchange_scan_barcode(self):
        if self.scan_barcode and len(self.scan_barcode) == 13:
            product = self.env['product.product'].search([('barcode', '=', self.scan_barcode)], limit=1)
            if not product:
                raise ValidationError("No product found for barcode %s" % self.scan_barcode)

            self.order_line |= self.env['sale.order.line'].new({
                'product_id': product.id,
                'product_uom_qty': self.scan_quantity,
                'product_uom': product.uom_id.id,
            })

            self.scan_barcode = ''  # Clear field to scan next
            self.scan_quantity = 1