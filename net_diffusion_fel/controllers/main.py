# -*- coding: utf-8 -*-
import logging
from werkzeug.exceptions import Forbidden, NotFound

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError
import json

from odoo.addons.net_diffusion.controllers.main import ShopCartFast

_logger = logging.getLogger(__name__)


class FELDiffusion(ShopCartFast):

    @http.route('/slider/products', type='json', auth='public', website=True)
    def slider_products(self, slider_id=None, limit=50, offset=0, **kwargs):
        """
        Return product data for a given slider (website.an_slider_products) for public user.
        This avoids frontend ORM ACL issues by using sudo and returning safe fields only.
        """
        if not slider_id:
            return {'products': [], 'total': 0}
        # ensure ints
        try:
            slider_id = int(slider_id)
            limit = int(limit or 50)
            offset = int(offset or 0)
        except Exception:
            limit = 50
            offset = 0
        env = request.env
        # Fetch slider lines in order
        Line = env['website.an_slider_product'].sudo()
        domain = [('slider_id', '=', slider_id)]
        total = Line.search_count(domain)
        lines = Line.search(domain, order='sequence asc, id asc', limit=limit, offset=offset)
        product_tmpl_ids = [l.product_id.id for l in lines if l.product_id]
        products = env['product.template'].sudo().browse(product_tmpl_ids).exists()

        # Pricelist for price computation similar to catalogue
        website = env['website'].get_current_website()
        pricelist = None
        try:
            order = request.website.sale_get_order() if hasattr(request, 'website') else None
            pricelist = order.pricelist_id if order and getattr(order, 'pricelist_id', False) else None
        except Exception:
            pricelist = None
        if not pricelist:
            try:
                if hasattr(request, 'website') and hasattr(request.website, 'get_current_pricelist'):
                    pricelist = request.website.get_current_pricelist()
            except Exception:
                pricelist = None
        if not pricelist:
            partner_pl = env.user.partner_id.property_product_pricelist
            pricelist = partner_pl or (website.pricelist_id if website else None)

        ProductProduct = env['product.product'].sudo()
        res = []
        for pt in products:
            variant = ProductProduct.search([('product_tmpl_id', '=', pt.id)], limit=1)
            # price computation
            price = pt.list_price
            try:
                if pricelist and hasattr(pricelist, '_get_product_price'):
                    price = pricelist._get_product_price(pt, 1.0)
                elif pricelist and hasattr(pricelist, 'price_get'):
                    price = pricelist.price_get(pt.id, 1.0).get(pricelist.id, pt.list_price)
            except Exception:
                price = pt.list_price
            # build payload expected by net_diffusion_fel.products_ajax template
            res.append({
                'id': pt.id,
                'variant': variant.id if variant else None,
                'name': pt.name or '',
                'website_url': pt.website_url or '#',
                'editeur': getattr(pt, 'editeur', '') or '',
                'auteur': getattr(pt, 'auteur', '') or '',
                'barcode': pt.barcode or '',
                'collection': getattr(pt, 'collection', '') or '',
                'price': round(price, 2) if isinstance(price, (int, float)) else price,
                'base_price': round(pt.list_price, 2) if isinstance(pt.list_price, (int, float)) else pt.list_price,
                'description_ecommerce': pt.description_ecommerce or '',
                'type_livre': getattr(pt, 'type_livre', '') or '',
                'date_parution': pt.date_parution.strftime('%d/%m/%Y') if getattr(pt, 'date_parution', False) else '',
                'dilicom_url': getattr(pt, 'dilicom_url', '') or '',
                'dilicom_url_thumb': getattr(pt, 'dilicom_url_thumb', '') or '',
                'token': getattr(pt, 'dilicom_url', '') or '',
                'csrf_token': request.csrf_token(),
                'disponibility_name': pt.dr_label_id.name if getattr(pt, 'dr_label_id', False) else '',
                'disponibility_color': pt.dr_label_id.text_color if getattr(pt, 'dr_label_id', False) else '',
                'disponibility_color_bck': pt.dr_label_id.background_color if getattr(pt, 'dr_label_id', False) else '',
                'disponibility_id': pt.dr_label_id.id if getattr(pt, 'dr_label_id', False) else None,
            })
        return {'products': res, 'total': total, 'offset': offset, 'limit': limit}

    @http.route('/slider/published', type='json', auth='public', website=True)
    def slider_published(self):
        # Adjust fields as needed
        fields = ['id', 'title', 'name', 'website_sequence']
        recs = request.env['website.an_slider_products'].sudo().search_read(
            [('publish', '=', True)], fields, order='website_sequence asc'
        )
        return recs

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>',
        '/catalogue'], type='http', auth="public", website=True)
    def catalogue_page(self,category=None,page=1, **post):
        disponibilities = request.env['dr.product.label'].search([('id', '!=', 2)])
        return request.render('net_diffusion_fel.catalogue_page_template', {
            'disponibilities': disponibilities,
        })


    @http.route(['/catalogue/categories'], type='json', auth="public", website=True)
    def catalogue_categories(self, parent_id=None, **kw):
        domain = [('parent_id', '=', int(parent_id))] if parent_id else [('parent_id', '=', False)]
        cats = request.env['product.public.category'].sudo().search(domain, order='name')
        res = []
        for c in cats:
            res.append({
                'id': c.id,
                'name': c.name,
                'has_children': bool(c.child_id),
            })
        return res


    @http.route(['/catalogue-ajax'], type='json', auth="public", website=True)
    def catalogue_page_ajax(self, search=None, page=1, limit=9, **post):

        url = '/catalogue'
        website = request.env['website'].get_current_website()
        # Robust pricelist retrieval compatible across versions/environments
        pricelist = None
        try:
            # Try website sale order pricelist first
            order = request.website.sale_get_order() if hasattr(request, 'website') else None
            pricelist = order.pricelist_id if order and getattr(order, 'pricelist_id', False) else None
        except Exception:
            pricelist = None
        if not pricelist:
            try:
                # Try method if available on website
                if hasattr(request, 'website') and hasattr(request.website, 'get_current_pricelist'):
                    pricelist = request.website.get_current_pricelist()
            except Exception:
                pricelist = None
        if not pricelist:
            # Fallbacks: partner pricelist then website default pricelist
            partner_pl = request.env.user.partner_id.property_product_pricelist
            pricelist = partner_pl or (website.pricelist_id if website else None)
        # Domain construction
        search_domain = [('active', '=', True), ('website_published', '=', True)]
        title = post.get('title') or ''
        editeur = post.get('editeur') or ''
        auteur = post.get('auteur') or ''
        collection = post.get('collection') or ''
        ean = post.get('ean') or ''
        disponibility = post.get('disponibility') or ''
        date_from = post.get('date_from') or ''
        date_to = post.get('date_to') or ''
        category_id = post.get('category_id')

        if title:
            search_domain.append(('name', 'ilike', title))
        if editeur:

            search_domain.append(('editeur', 'ilike', editeur))
        if auteur:
            search_domain.append(('auteur', 'ilike', auteur))
        if collection:
            search_domain.append(('collection', 'ilike', collection))
        if ean:
            search_domain.append(('barcode', 'ilike', ean))
        if disponibility:
            # dr_label_id is a many2one, filter by id
            try:
                search_domain.append(('dr_label_id', '=', int(disponibility)))
            except Exception:
                pass
        # Date range on date_parution (Date field)
        if date_from:
            search_domain.append(('date_parution', '>=', date_from))
        if date_to:
            search_domain.append(('date_parution', '<=', date_to))
        # Public category (product.public.category via categ_ids many2many)
        if category_id:
            try:
                search_domain.append(('public_categ_ids', 'in', int(category_id)))
            except Exception:
                pass

        Product = request.env['product.template'].sudo()
        products_count = Product.search_count(search_domain)
        pager_data = website.pager(url=url, total=products_count, page=int(page or 1), step=int(limit or 50))
        # Be defensive: some environments may not include 'step' in the pager response
        if not isinstance(pager_data, dict):
            pager_data = {}
        step_val = pager_data.get('step', int(limit or 50))
        offset = pager_data.get('offset', 0)
        # ensure keys present for frontend logic
        pager_data['step'] = step_val
        pager_data['offset'] = offset
        pager_data['total'] = products_count
        products = Product.search(search_domain, limit=step_val, offset=offset, order='date_parution desc, name asc')

        products_data = []
        ProductProduct = request.env['product.product'].sudo()
        for product in products:
            product_variant = ProductProduct.search([('product_tmpl_id', '=', product.id)], limit=1)
            price = 0.0
            try:
                if pricelist and hasattr(pricelist, '_get_product_price'):
                    price = pricelist._get_product_price(product, 1.0)
                elif pricelist and hasattr(pricelist, 'price_get'):
                    price = pricelist.price_get(product.id, 1.0).get(pricelist.id, product.list_price)
                elif pricelist and hasattr(pricelist, '_price_get'):
                    price = pricelist._price_get(product, 1).get(1)
                else:
                    price = product.list_price
            except Exception:
                price = product.list_price
            products_data.append({
                'id': product.id,
                'variant': product_variant.id if product_variant else None,
                'name': product.name or '',
                'website_url': product.website_url or '#',
                'editeur': getattr(product, 'editeur', '') or '',
                'auteur': getattr(product, 'auteur', '') or '',
                'barcode': product.barcode or '',
                'collection': getattr(product, 'collection', '') or '',
                'price': price,
                'base_price': product.list_price,
                'description_ecommerce': product.description_ecommerce or '',
                'type_livre': getattr(product, 'type_livre', '') or '',
                'date_parution': product.date_parution.strftime('%d/%m/%Y') if product.date_parution else '',
                'dilicom_url': getattr(product, 'dilicom_url', '') or '',
                'token': getattr(product, 'dilicom_url', '') or '',
                'csrf_token': request.csrf_token(),
                'disponibility_name': product.dr_label_id.name if getattr(product, 'dr_label_id', False) else '',
                'disponibility_color': product.dr_label_id.text_color if getattr(product, 'dr_label_id', False) else '',
                'disponibility_color_bck': product.dr_label_id.background_color if getattr(product, 'dr_label_id',
                                                                                           False) else '',
                'disponibility_id': product.dr_label_id.id if getattr(product, 'dr_label_id', False) else None,
            })
        return {'products': products_data, 'pager': pager_data}