# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date, datetime

class Office(models.Model):
    _name = 'diffusion.office'
    _description = 'Diffusion Office'
    _inherit = ['website.published.mixin', 'website.seo.metadata', 'website.multi.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    date_limit = fields.Date(string='Date Limit', required=True)
    delivery_date = fields.Date(string='Delivery Date', required=True)
    theme_id = fields.Many2one('diffusion.office.category', string='Theme', required=True)
    image = fields.Image(string='Image Web')

    # Website fields
    website_id = fields.Many2one('website', string='Website')
    is_published = fields.Boolean(default=True)
    
    # Product related fields
    product_ids = fields.Many2many('product.template', string='Products')
    product_count = fields.Integer(compute='_compute_product_count', string='Product Count')
    scan_barcode = fields.Char(string='Produit Scan Barcode', help='Scan a product barcode to add it to this office')

    @api.onchange('scan_barcode')
    def _onchange_scan_barcode(self):
        if self.scan_barcode and len(self.scan_barcode) == 13:
            product = self.env['product.template'].search([('barcode', '=', self.scan_barcode)], limit=1)
            if not product:
                raise ValidationError("No product found for barcode %s" % self.scan_barcode)

            # Ajouter le produit au champ Many2many product_ids
            if product.id not in self.product_ids.ids:
                self.product_ids = [(4, product.id)]  # (4, id) pour ajouter une relation existante

            self.scan_barcode = ''  # Vider le champ pour scanner le suivant

    @api.depends('product_ids')
    def _compute_product_count(self):
        for office in self:
            office.product_count = len(office.product_ids)
    
    @api.constrains('date_limit', 'delivery_date')
    def _check_dates(self):
        for office in self:
            if office.date_limit and office.delivery_date and office.date_limit > office.delivery_date:
                raise ValidationError(_('The delivery date must be after the date limit.'))
    
    def generate_products(self):
        """Generate products with code_disponibility = 2 for this office"""
        self.ensure_one()
        
        # Get all products from the theme category
        category_products = self.env['product.template'].search([
            ('categ_id', '=', self.theme_id.product_category_id.id)
        ])
        
        for product in category_products:
            # Create a copy of the product with code_disponibility = 2
            new_product = product.copy({
                'name': f"{product.name} - {self.name}",
                'office_id': self.id,
                'code_disponibility': '2',  # Set code_disponibility to 2
                'website_published': True,
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        
    def action_view_products(self):
        """Open the products linked to this office"""
        self.ensure_one()
        return {
            'name': _('Products'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('office_id', '=', self.id)],
            'context': {'search_default_code_disponibility_2': 1},
        }