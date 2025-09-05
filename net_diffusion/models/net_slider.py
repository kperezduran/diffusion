# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WebsiteNetSliderInjection(models.Model):
    _name = 'website.net_slider_injection'
    _description = 'Net Slider Dynamic Injection'
    _order = 'sequence asc'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    slider_id = fields.Many2one('website.an_slider_products', string='Slider', required=True)
    page_url = fields.Char(string='Page URL', help='Absolute or relative URL where this slider should appear (e.g., /shop).')
    css_selector = fields.Char(string='CSS Selector', required=True, help='DOM selector where the slider HTML will be injected.')

    website_ids = fields.Many2many('website', 'website_net_slider_inj_rel', 'injection_id', 'website_id', string='Websites')
    language_ids = fields.Many2many('res.lang', 'lang_net_slider_inj_rel', 'injection_id', 'lang_id', string='Languages')

    date_from = fields.Datetime(string='Start Date')
    date_to = fields.Datetime(string='End Date')

    publish = fields.Boolean(string='Published', default=True)

    def _is_active_now(self):
        now = fields.Datetime.now()
        self.ensure_one()
        if not self.active or not self.publish:
            return False
        if self.date_from and self.date_from > now:
            return False
        if self.date_to and self.date_to < now:
            return False
        return True
