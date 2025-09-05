# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    office_ids = fields.Many2many('diffusion.office', string='Offices', index=True)
