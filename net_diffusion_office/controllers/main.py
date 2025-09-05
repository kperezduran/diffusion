# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.http_routing.models.ir_http import slug
import re
from datetime import date, datetime


class OfficeController(WebsiteSale):
    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(
        self, product_id, add_qty=1, set_qty=0,
        product_custom_attribute_values=None, no_variant_attribute_values=None,
        express=False, **kwargs
    ):
        """Override to create office orders when products are added from an office."""
        # Check if the request is coming from an office page
        referer = request.httprequest.headers.get('Referer', '')
        office_id = kwargs.get('office_id')
        
        # If office_id is provided in the form, use it
        if office_id:
            office_id = int(office_id)
            office = request.env['diffusion.office'].browse(office_id)
            
            # Check if today is after the date limit
            today = date.today()
            if today > office.date_limit:
                # After date limit, proceed with normal cart update
                return super(OfficeController, self).cart_update(
                    product_id=product_id,
                    add_qty=add_qty,
                    set_qty=set_qty,
                    product_custom_attribute_values=product_custom_attribute_values,
                    no_variant_attribute_values=no_variant_attribute_values,
                    express=express,
                    **kwargs
                )
        
        # Extract office_id from referer if it's an office page and not provided in form
        if not office_id:
            office_match = re.search(r'/office/diffusion.office_(\d+)', referer)
            if office_match:
                office_id = int(office_match.group(1))
        
        # If no office_id in referer, check if the product is associated with an office
        if not office_id:
            product = request.env['product.product'].browse(int(product_id))
            if product.exists() and product.product_tmpl_id.office_ids:
                # If product is in multiple offices, use the first one
                office_id = product.product_tmpl_id.office_ids[0].id
        
        # Continue with normal cart update (no office order creation)
        return super(OfficeController, self).cart_update(
            product_id=product_id,
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values,
            express=express,
            **kwargs
        )
        
    @http.route(['/office/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def office_cart_update(
        self, product_id, office_id, add_qty=1, set_qty=0, **kwargs
    ):
        """Add products to office order."""
        if request.website.is_public_user():
            return request.redirect('/web/login?redirect=/offices')
            
        # Get the office
        office = request.env['diffusion.office'].browse(int(office_id))
        if not office.exists():
            return request.redirect('/offices')
            
        # Check if today is before the date limit
        today = date.today()
        if today > office.date_limit:
            # After date limit, redirect to regular cart
            return request.redirect('/shop/cart/update?product_id=%s&add_qty=%s' % (product_id, add_qty))
            
        # Create or update office order
        partner_id = request.env.user.partner_id.id
        office_order = request.env['diffusion.office.order'].sudo().get_office_order(
            partner_id=partner_id,
            office_id=int(office_id)
        )
        
        # Add product to office order
        product = request.env['product.product'].browse(int(product_id))
        if product.exists():
            # Check if product already exists in order lines
            order_line = request.env['diffusion.office.order.line'].sudo().search([
                ('order_id', '=', office_order.id),
                ('product_id', '=', int(product_id))
            ], limit=1)
            
            if order_line:
                # Update existing line
                new_qty = order_line.product_uom_qty + float(add_qty)
                order_line.write({
                    'product_uom_qty': new_qty
                })
            else:
                # Create new line
                request.env['diffusion.office.order.line'].sudo().create({
                    'order_id': office_order.id,
                    'product_id': int(product_id),
                    'product_uom_qty': float(add_qty),
                    'price_unit': product.list_price
                })
        
        # Redirect to office order cart page
        return request.redirect('/office/cart')
        
    @http.route(['/office/cart'], type='http', auth="public", website=True)
    def office_cart(self, **kwargs):
        """Display the office order cart."""
        if request.website.is_public_user():
            return request.redirect('/web/login?redirect=/office/cart')
            
        # Get all draft office orders for the current user
        partner_id = request.env.user.partner_id.id
        orders = request.env['diffusion.office.order'].sudo().search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'draft')
        ])
        
        values = {
            'orders': orders,
            'today': date.today(),
        }
        
        return request.render('net_diffusion_office.office_cart', values)
        
    @http.route(['/office/cart/update_qty'], type='http', auth="public", methods=['POST'], website=True)
    def office_cart_update_qty(self, line_id, quantity, **kwargs):
        """Update the quantity of a product in the office order."""
        if request.website.is_public_user():
            return request.redirect('/web/login?redirect=/office/cart')
            
        # Get the order line
        order_line = request.env['diffusion.office.order.line'].sudo().browse(int(line_id))
        
        # Check if the order line belongs to the current user
        if order_line.order_id.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/office/cart')
            
        # Update the quantity
        try:
            quantity = float(quantity)
            if quantity <= 0:
                # Remove the line if quantity is 0 or negative
                order_line.unlink()
            else:
                order_line.write({'product_uom_qty': quantity})
        except:
            pass
            
        return request.redirect('/office/cart')
        
    @http.route(['/office/cart/remove'], type='http', auth="public", website=True)
    def office_cart_remove(self, line_id, **kwargs):
        """Remove a product from the office order."""
        if request.website.is_public_user():
            return request.redirect('/web/login?redirect=/office/cart')
            
        # Get the order line
        order_line = request.env['diffusion.office.order.line'].sudo().browse(int(line_id))
        
        # Check if the order line belongs to the current user
        if order_line.order_id.partner_id.id != request.env.user.partner_id.id:
            return request.redirect('/office/cart')
            
        # Remove the line
        order_line.unlink()
            
        return request.redirect('/office/cart')
        
    @http.route(['/office/orders'], type='http', auth="public", website=True)
    def office_orders(self, **kwargs):
        """Display all office orders for the current user."""
        if request.website.is_public_user():
            return request.redirect('/web/login?redirect=/office/orders')
            
        # Get all office orders for the current user
        partner_id = request.env.user.partner_id.id
        orders = request.env['diffusion.office.order'].sudo().search([
            ('partner_id', '=', partner_id)
        ], order='create_date desc')
        
        values = {
            'orders': orders,
        }
        
        return request.render('net_diffusion_office.office_orders', values)
    
    @http.route([
        '/offices',
        '/offices/page/<int:page>',
    ], type='http', auth='public', website=True)
    def offices(self, page=0, **kwargs):
        """Display all offices"""
        Office = request.env['diffusion.office']
        
        # Get all published offices
        domain = [('is_published', '=', True)]
        if not request.env.user.has_group('base.group_user'):
            domain.append(('website_id', 'in', (False, request.website.id)))
            
        # Count total offices
        offices_count = Office.search_count(domain)
        
        # Pagination
        pager = request.website.pager(
            url='/offices',
            total=offices_count,
            page=page,
            step=12,
        )
        
        # Get offices for current page
        offices = Office.search(domain, limit=12, offset=pager['offset'])
        
        values = {
            'offices': offices,
            'pager': pager,
            # 'main_object': offices,
        }
        
        return request.render('net_diffusion_office.offices', values)
    
    @http.route([
        '/office/<model("diffusion.office"):office>',
        '/office/<model("diffusion.office"):office>/page/<int:page>',
    ], type='http', auth='public', website=True)
    def office(self, office, page=0, category=None, search='', **kwargs):
        """Display a specific office and its products"""
        if not office.can_access_from_current_website():
            raise request.not_found()
            
        # Get all products with code_disponibility = 2 for this office
        domain = [
            ('id', 'in', office.product_ids.ids),
            ('code_disponibility', 'in', ('1','2')),
            ('website_published', '=', True),
        ]
        
        # Add website domain
        if not request.env.user.has_group('base.group_user'):
            domain.append(('website_id', 'in', (False, request.website.id)))
            
        # Search functionality
        if search:
            domain += [
                '|', '|', '|',
                ('name', 'ilike', search),
                ('description', 'ilike', search),
                ('description_sale', 'ilike', search),
                ('product_variant_ids.default_code', 'ilike', search),
            ]
            
        # Category filter
        if category:
            category = request.env['product.public.category'].browse(int(category))
            if category.exists():
                domain += [('public_categ_ids', 'child_of', int(category))]
                
        # Count total products
        Product = request.env['product.template']
        product_count = Product.search_count(domain)
        
        # Pagination
        pager = request.website.pager(
            url='/office/%s' % slug(office),
            total=product_count,
            page=page,
            step=20,
            url_args={'category': category and category.id, 'search': search},
        )
        
        # Get products for current page
        products = Product.search(domain, limit=20, offset=pager['offset'])
        
        # Query URL for filters
        keep = QueryURL('/office/%s' % slug(office), category=category and category.id, search=search)
        
        # Get categories for filter
        categories = request.env['product.public.category'].search([])
        
        # Get today's date for comparison with office.date_limit
        today = date.today()
        
        values = {
            'office': office,
            'products': products,
            'categories': categories,
            'pager': pager,
            'keep': keep,
            'search': search,
            'category': category,
            'main_object': office,
            'today': today,
        }
        
        return request.render('net_diffusion_office.office', values)