# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class NetSliderController(http.Controller):

    @http.route(['/net_slider/config'], type='json', auth='public', website=True, csrf=False)
    def net_slider_config(self, url=None, **kwargs):
        website = request.env['website'].get_current_website()
        lang = request.lang and request.lang.split('_')[0] or False
        domain = [('active', '=', True), ('publish', '=', True)]
        if url:
            domain += ['|', ('page_url', '=', url), ('page_url', '=', request.httprequest.path)]
        # Filter website and language if set
        injections = request.env['website.net_slider_injection'].sudo().search(domain, order='sequence asc')
        result = []
        for inj in injections:
            if inj.website_ids and website.id not in inj.website_ids.ids:
                continue
            if inj.language_ids and request.lang not in inj.language_ids.mapped('code'):
                continue
            if not inj._is_active_now():
                continue
            result.append({
                'id': inj.id,
                'css_selector': inj.css_selector,
            })
        return result

    @http.route(['/net_slider/render/<int:inj_id>'], type='json', auth='public', website=True, csrf=False)
    def net_slider_render(self, inj_id, **kwargs):
        inj = request.env['website.net_slider_injection'].sudo().browse(int(inj_id))
        if not inj or not inj.exists() or not inj._is_active_now():
            return {'html': ''}
        slider = inj.slider_id
        # Prepare context variables for template
        values = {
            'sliderj': slider,
            'slides': slider.slider_product_ids,
            'languages': request.env['res.lang'].sudo().get_installed(),
            'lang': request.lang,
            'add_qty': 1,
        }
        html = request.env['ir.ui.view']._render_template('net_diffusion.net_slider_container', values)
        return {'html': html}
