# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class OfficeCategory(models.Model):
    _name = 'diffusion.office.category'
    _description = 'Office Category'
    _inherit = ['website.published.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    
    # Link to product category
    product_category_id = fields.Many2one(
        'product.category', 
        string='Product Category', 
        required=True,
        help='Products from this category will be used to generate office products'
    )
    
    # Website fields
    website_id = fields.Many2one('website', string='Website')
    is_published = fields.Boolean(default=True)
    
    # Related offices
    office_ids = fields.One2many('diffusion.office', 'theme_id', string='Offices')
    office_count = fields.Integer(compute='_compute_office_count', string='Office Count')
    
    @api.depends('office_ids')
    def _compute_office_count(self):
        for category in self:
            category.office_count = len(category.office_ids)
    
    def action_view_offices(self):
        """Open the offices linked to this category"""
        self.ensure_one()
        return {
            'name': _('Offices'),
            'type': 'ir.actions.act_window',
            'res_model': 'diffusion.office',
            'view_mode': 'tree,form',
            'domain': [('theme_id', '=', self.id)],
        }
    
    def action_view_products(self):
        """Open the products linked to this category"""
        self.ensure_one()
        return {
            'name': _('Products'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('categ_id', '=', self.product_category_id.id)],
        }