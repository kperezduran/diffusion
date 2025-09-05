# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
import re
from pymongo import MongoClient, ASCENDING
from odoo.exceptions import ValidationError, UserError

import datetime

try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class StockPicking(models.Model):
    _inherit = "stock.picking"

    quantity_total = fields.Float(string='Quantity Total', compute='_compute_quantity_total')
    quantity_processed = fields.Float(string='Quantité en cours', compute='_compute_quantity_total')
    url_download = fields.Char(string='Lien téléchargement', compute='_compute_link')
    is_credited = fields.Boolean(string='Déjà crédité', default=False)

    def create_note_credit(self):
        self.ensure_one()  # Ensure single picking operation


        partner = self.partner_id
        pricelist = partner.property_product_pricelist

        # Ensure pricelist has a valid currency
        if not pricelist or not pricelist.currency_id:
            raise UserError("The selected pricelist does not have a valid currency assigned.")

        # Check if the currency conversion rate is available
        currency_rate = pricelist.currency_id.rate
        if not currency_rate or currency_rate == 0:
            raise UserError(
                f"No valid exchange rate found for currency {pricelist.currency_id.name}. Please update currency rates.")

        invoice_lines = []
        for move in self.move_ids_without_package:
            product = move.product_id
            quantity = move.quantity  # Consider only delivered quantity

            if quantity > 0:
                # Fetch price and discount from pricelist, handling errors
                try:
                    price, rule = pricelist._get_product_price_rule(product, quantity, partner)
                except Exception:
                    price = product.lst_price  # Fallback to list price if rule fails
                    rule = None

                discount = 0.0
                if rule and rule.compute_price == 'formula' and rule.base == 'list_price':
                    list_price = product.lst_price
                    if list_price > 0:
                        discount = ((list_price - price) / list_price) * 100

                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'quantity': quantity,
                    'price_unit': price,  # Use computed price
                    'discount': discount,  # Apply discount if applicable
                    'name': product.display_name,
                    'account_id': product.categ_id.property_account_income_categ_id.id,
                    'tax_ids': [(6, 0, product.taxes_id.ids)],  # Apply correct taxes
                }))

        if not invoice_lines:
            raise UserError("No processed products available for credit note creation.")

        # Create credit note (account.move)
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': partner.id,
            'invoice_line_ids': invoice_lines,
            'currency_id': pricelist.currency_id.id,
            'journal_id': 10,
        })

        self.write({'is_credited': True})
        return {
            'name': 'Credit Note',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': credit_note.id,
        }



    def _compute_link(self):
        for rec in self:
            rec.url_download = f'/my/orders/download_picking_xlsx?picking_id={rec.id}'

    def _compute_quantity_total(self):
        for rec in self:
            quantity_temp = 0
            qt_temp = 0
            if rec.move_line_ids:
                quantity_temp = sum(rec.move_line_ids.mapped('quantity'))
                qt_temp = sum(rec.move_ids.mapped('product_uom_qty'))
                rec.quantity_total += quantity_temp
                rec.quantity_processed += qt_temp
            else:
                rec.quantity_total = quantity_temp
                rec.quantity_processed = qt_temp


class StockMove(models.Model):
    _inherit = "stock.move"

    barcode = fields.Char(string="EAN", related="product_id.barcode")
    localisation = fields.Char(string="Localisation", related="product_id.localisation")
    disponibility = fields.Char(string="Disponibilité", related="product_id.code_disponibility")
    supplier = fields.Many2one("res.partner", compute='_compute_infos_line', string="Fournisseur")
    date_parution = fields.Date(string="Date de parution", related="product_id.date_parution")

    def _compute_quantity_total(self):
        for rec in self:
            quantity_temp = 0
            if rec.move_line_ids:
                quantity_temp = sum(rec.move_line_ids.mapped('quantity'))
                rec.quantity_total += quantity_temp
            else:
                rec.quantity_total = 0

    def _compute_infos_line(self):
        for record in self:
            if record.product_id:
                if record.product_id.variant_seller_ids:
                    record.supplier = record.product_id.variant_seller_ids[0].partner_id.id
                else:
                    record.supplier = None

class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    quantity_total = fields.Float(string='Quantity Total', compute='_compute_quantity_total')

    def _compute_quantity_total(self):
        for rec in self:
            quantity_temp = 0
            if rec.move_line_ids:
                quantity_temp = sum(rec.move_line_ids.mapped('quantity_product_uom'))
                rec.quantity_total += quantity_temp
            else:
                rec.quantity_total = 0
