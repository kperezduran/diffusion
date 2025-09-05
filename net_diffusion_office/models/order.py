# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OfficeOrder(models.Model):
    _name = 'diffusion.office.order'
    _description = 'Office Order'
    _order = 'create_date desc'

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, 
                       default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    office_id = fields.Many2one('diffusion.office', string='Office', required=True)
    date_order = fields.Datetime(string='Order Date', required=True, default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    order_line_ids = fields.One2many('diffusion.office.order.line', 'order_id', string='Order Lines')
    amount_total = fields.Float(string='Total', compute='_compute_amount_total', store=True)
    
    @api.depends('order_line_ids.price_subtotal')
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = sum(line.price_subtotal for line in order.order_line_ids)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('diffusion.office.order') or _('New')
        return super(OfficeOrder, self).create(vals_list)
    
    def action_confirm(self):
        self.write({'state': 'confirmed'})
    
    def action_done(self):
        self.write({'state': 'done'})
    
    def action_cancel(self):
        self.write({'state': 'cancel'})
    
    def action_draft(self):
        self.write({'state': 'draft'})
    
    @api.model
    def get_office_order(self, partner_id, office_id):
        """Get or create an office order for the given partner and office"""
        order = self.search([
            ('partner_id', '=', partner_id),
            ('office_id', '=', office_id),
            ('state', '=', 'draft')
        ], limit=1)
        
        if not order:
            order = self.create({
                'partner_id': partner_id,
                'office_id': office_id,
            })
        
        return order


class OfficeOrderLine(models.Model):
    _name = 'diffusion.office.order.line'
    _description = 'Office Order Line'

    order_id = fields.Many2one('diffusion.office.order', string='Order', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_qty = fields.Float(string='Quantity', required=True, default=1.0)
    price_unit = fields.Float(string='Unit Price', required=True)
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal', store=True)
    
    @api.depends('product_uom_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_uom_qty * line.price_unit
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price