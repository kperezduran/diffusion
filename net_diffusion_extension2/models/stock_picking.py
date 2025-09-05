# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


# class StockMove(models.Model):
#     _inherit = 'stock.move'
#
#     editeur = fields.Char(string="Editeur", related="product_id.editeur", store=True, compute='_compute_field_x',
#                           readonly=True)
#     barcode = fields.Char(string="EAN", related="product_id.barcode", store=True, compute='_compute_field_x',
#                           readonly=True)
#     localisation = fields.Char(string="Localisation", related="product_id.localisation", store=True,
#                                compute='_compute_field_x', readonly=True)
#     disponibility = fields.Char(string="Disponibilité", related="product_id.code_disponibility", store=True,
#                                 compute='_compute_field_x', readonly=True)
#     date_parution = fields.Date(string="Date de parution", related="product_id.date_parution", store=True,
#                                 compute='_compute_field_x', readonly=True)
#
#     @api.depends('product_id.editeur', 'product_id.barcode', 'product_id.localisation', 'product_id.code_disponibility',
#                  'product_id.date_parution')
#     def _compute_field_x(self):
#         for record in self:
#             record.editeur = record.product_id.editeur
#             record.localisation = record.product_id.localisation
#             record.disponibility = record.product_id.disponibility
#             record.date_parution = record.product_id.date_parution
#             record.barcode = record.product_id.barcode


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    scan_barcode = fields.Char(string="Scan Barcode")
    scan_quantity = fields.Integer(string="Scan Quantité", default=1, help="Quantity to add when scanning a barcode")

    @api.onchange('scan_barcode')
    def _onchange_scan_barcode(self):
        if self.scan_barcode and len(self.scan_barcode) == 13:
            product = self.env['product.product'].search([('barcode', '=', self.scan_barcode)], limit=1)
            if not product:
                raise ValidationError("No product found for barcode %s" % self.scan_barcode)

            self.move_ids_without_package |= self.env['stock.move'].new({
                'name': product.display_name,
                'product_id': product.id,
                'product_uom_qty': self.scan_quantity,
                'product_uom': product.uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'picking_id': self.id,
            })

            self.scan_barcode = ''  # Clear field to scan next
            self.scan_quantity = 1  # Clear field to scan next
