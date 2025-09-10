# -*- coding: utf-8 -*-
import logging
from werkzeug.exceptions import Forbidden, NotFound

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError
import json

from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_sale.controllers.main import WebsiteSale
from datetime import datetime
import xlsxwriter
import io
import base64

_logger = logging.getLogger(__name__)


class ShopCartFast(WebsiteSale):

    @http.route(['/rapport_stock/<int:stock_id>'], type='http', auth="public", website=True)
    def download_stock_rapport(self, stock_id=None, **kwargs):
        if stock_id:
            location = request.env['stock.location'].sudo().browse(int(stock_id))
            quant_ids = location.quant_ids
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})

            # Define formats
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
            center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            red_format = workbook.add_format({'bg_color': '#FF9999', 'align': 'center', 'valign': 'vcenter'})

            worksheet = workbook.add_worksheet('Rapport stock')

            # Headers
            headers = ['Produit', 'Quantités en stock', 'Quantités disponibles', 'Quantités réservés',
                           'Barcode (Image)', 'Barcode (Numéro)', 'Date de parution', 'Auteur', 'Editeur', 'Collection']
            worksheet.set_row(0, 30)  # Header row height

            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            # Set column widths
            column_widths = [45, 10, 15, 8, 12, 25, 17, 25, 15, 20]
            for col, width in enumerate(column_widths):
                worksheet.set_column(col, col, width)

            row = 1
            for quant in quant_ids:
                product = quant.product_id
                product_template = product.product_tmpl_id

                # Retrieve the tax rate from the product's associated taxes
                tax_rate = 1.0  # Default to 1 (no tax) if no tax is found
                if product.taxes_id:
                    # Assuming the first tax is the primary one to apply; you may need to adjust if multiple taxes exist
                    primary_tax = product.taxes_id[0]
                    tax_rate = 1 + (primary_tax.amount / 100)

                # Write basic details with dynamic tax rate
                worksheet.write(row, 0, product.display_name, center_format)
                worksheet.write(row, 2, quant.quantity, center_format)
                worksheet.write(row, 1, quant.available_quantity, center_format)
                worksheet.write(row, 3, quant.reserved_quantity, center_format)

                # Add Barcode as Image and Numeric Value
                if product.barcode:
                    # Numeric barcode value
                    worksheet.write(row, 5, product.barcode, center_format)

                    # Generate Barcode Image
                    barcode_img = request.env['ir.actions.report'].barcode(
                        'EAN13', product.barcode, width=300, height=100
                    )
                    image_data = io.BytesIO(barcode_img)

                    # Set row height to 52px for barcode rows only
                    worksheet.set_row(row, 52)

                    # Insert image
                    worksheet.insert_image(row, 4, 'barcode.png',
                                           {'image_data': image_data, 'x_scale': 0.5, 'y_scale': 0.5})
                if product_template.date_parution:
                    worksheet.write(row, 6, product_template.date_parution.strftime('%d/%m/%Y') or "", center_format)
                # Write Author, Publisher, Collection information with conditional format
                worksheet.write(row, 7, product_template.auteur or "", center_format)
                worksheet.write(row, 8, product_template.editeur or "", center_format)
                worksheet.write(row, 9, product_template.collection or "", center_format)
                #
                row += 1

            workbook.close()

            # Prepare response
            output.seek(0)
            filename = f"Rapport Emplacement{location.name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            headers = [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}'),
            ]
            return request.make_response(output.read(), headers=headers)

    @http.route(['/my/orders/download_picking_xlsx'], type='http', auth="public", website=True)
    def download_picking_xlsx(self, id=None, picking_id=None, **kwargs):

        if id:
            sale_order = request.env['sale.order'].sudo().browse(int(id))
            picking_ids = sale_order.picking_ids# Generate Excel file
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})

            # Define formats
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
            center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            red_format = workbook.add_format({'bg_color': '#FF9999', 'align': 'center', 'valign': 'vcenter'})

            for picking in picking_ids:
                worksheet = workbook.add_worksheet(picking.name[:31])

                # Add a note if this picking is a backorder
                backorder_info = "Backorder" if picking.backorder_id else "Commande"
                worksheet.write(0, 0, backorder_info, header_format)

                # Headers
                headers = ['Produit', 'HTVA', 'TTC', 'Quantités', 'Quantités livrés',
                           'Barcode (Image)', 'Barcode (Numéro)', 'Date de parution', 'Auteur', 'Editeur', 'Collection']
                worksheet.set_row(1, 30)  # Header row height

                for col, header in enumerate(headers):
                    worksheet.write(1, col, header, header_format)

                # Set column widths
                column_widths = [45, 10, 15, 8, 12, 25, 17, 25, 15, 20]
                for col, width in enumerate(column_widths):
                    worksheet.set_column(col, col, width)

                row = 2
                for line in picking.move_ids_without_package:
                    product = line.product_id
                    product_template = product.product_tmpl_id

                    # Retrieve the tax rate from the product's associated taxes
                    tax_rate = 1.0  # Default to 1 (no tax) if no tax is found
                    if product.taxes_id:
                        # Assuming the first tax is the primary one to apply; you may need to adjust if multiple taxes exist
                        primary_tax = product.taxes_id[0]
                        tax_rate = 1 + (primary_tax.amount / 100)

                    # Write basic details with dynamic tax rate
                    worksheet.write(row, 0, product.display_name, center_format)
                    worksheet.write(row, 1, round(product.list_price / tax_rate,2), center_format)
                    worksheet.write(row, 2, product.list_price, center_format)
                    worksheet.write(row, 3, line.product_uom_qty, center_format)
                    worksheet.write(row, 4, line.quantity, center_format)

                    # Check if delivered quantity is less than ordered
                    format_to_use = center_format if line.quantity < line.product_uom_qty else center_format

                    # Add Barcode as Image and Numeric Value
                    if product.barcode:
                        # Numeric barcode value
                        worksheet.write(row, 6, product.barcode, center_format)

                        # Generate Barcode Image
                        barcode_img = request.env['ir.actions.report'].barcode(
                            'EAN13', product.barcode, width=300, height=100
                        )
                        image_data = io.BytesIO(barcode_img)

                        # Set row height to 52px for barcode rows only
                        worksheet.set_row(row, 52)

                        # Insert image
                        worksheet.insert_image(row, 5, 'barcode.png',
                                               {'image_data': image_data, 'x_scale': 0.5, 'y_scale': 0.5})
                    if product_template.date_parution:
                        worksheet.write(row, 7, product_template.date_parution.strftime('%d/%m/%Y') or "", format_to_use)
                    # Write Author, Publisher, Collection information with conditional format
                    worksheet.write(row, 8, product_template.auteur or "", format_to_use)
                    worksheet.write(row, 9, product_template.editeur or "", format_to_use)
                    worksheet.write(row, 10, product_template.collection or "", format_to_use)

                    row += 1

            workbook.close()

            # Prepare response
            output.seek(0)
            filename = f"Picking_List_{sale_order.name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            headers = [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}'),
            ]
            return request.make_response(output.read(), headers=headers)
        elif picking_id:
            picking_ids = request.env['stock.picking'].sudo().search([('id', '=', int(picking_id))])
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})

            # Define formats
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
            center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
            red_format = workbook.add_format({'bg_color': '#FF9999', 'align': 'center', 'valign': 'vcenter'})

            for picking in picking_ids:
                worksheet = workbook.add_worksheet(picking.name[:31])

                # Add a note if this picking is a backorder
                backorder_info = "Backorder" if picking.backorder_id else "Commande"
                worksheet.write(0, 0, backorder_info, header_format)

                # Headers
                headers = ['Produit', 'HTVA', 'TTC', 'Quantités', 'Quantités livrés',
                           'Barcode (Image)', 'Barcode (Numéro)', 'Date de parution', 'Auteur', 'Editeur', 'Collection']
                worksheet.set_row(1, 30)  # Header row height

                for col, header in enumerate(headers):
                    worksheet.write(1, col, header, header_format)

                # Set column widths
                column_widths = [45, 10, 15, 8, 12, 25, 17, 25, 15, 20]
                for col, width in enumerate(column_widths):
                    worksheet.set_column(col, col, width)

                row = 2
                for line in picking.move_ids_without_package:
                    product = line.product_id
                    product_template = product.product_tmpl_id

                    # Retrieve the tax rate from the product's associated taxes
                    tax_rate = 1.0  # Default to 1 (no tax) if no tax is found
                    if product.taxes_id:
                        # Assuming the first tax is the primary one to apply; you may need to adjust if multiple taxes exist
                        primary_tax = product.taxes_id[0]
                        tax_rate = 1 + (primary_tax.amount / 100)

                    # Write basic details with dynamic tax rate
                    worksheet.write(row, 0, product.display_name, center_format)
                    worksheet.write(row, 1, round(product.list_price / tax_rate,2), center_format)
                    worksheet.write(row, 2, product.list_price, center_format)
                    worksheet.write(row, 3, line.product_uom_qty, center_format)
                    worksheet.write(row, 4, line.quantity, center_format)

                    # Check if delivered quantity is less than ordered
                    format_to_use = center_format if line.quantity < line.product_uom_qty else center_format

                    # Add Barcode as Image and Numeric Value
                    if product.barcode:
                        # Numeric barcode value
                        worksheet.write(row, 6, product.barcode, center_format)

                        # Generate Barcode Image
                        barcode_img = request.env['ir.actions.report'].barcode(
                            'EAN13', product.barcode, width=300, height=100
                        )
                        image_data = io.BytesIO(barcode_img)

                        # Set row height to 52px for barcode rows only
                        worksheet.set_row(row, 52)

                        # Insert image
                        worksheet.insert_image(row, 5, 'barcode.png',
                                               {'image_data': image_data, 'x_scale': 0.5, 'y_scale': 0.5})
                    if product_template.date_parution:
                        worksheet.write(row, 7, product_template.date_parution.strftime('%d/%m/%Y') or "", format_to_use)
                    # Write Author, Publisher, Collection information with conditional format
                    worksheet.write(row, 8, product_template.auteur or "", format_to_use)
                    worksheet.write(row, 9, product_template.editeur or "", format_to_use)
                    worksheet.write(row, 10, product_template.collection or "", format_to_use)

                    row += 1

            workbook.close()

            # Prepare response
            output.seek(0)
            filename = f"Picking_List_{picking.name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            headers = [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}'),
            ]
            return request.make_response(output.read(), headers=headers)
        else:
            return request.not_found()

    @http.route(['/my/invoice/download_invoice_xlsx'], type='http', auth="public", website=True)
    def download_invoicexlsx(self, invoice_id=None, **kwargs):
        if invoice_id:
            invoice = request.env['account.move'].sudo().browse(int(invoice_id))
            if invoice:
                output = io.BytesIO()
                workbook = xlsxwriter.Workbook(output, {'in_memory': True})

                # Define formats
                header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
                center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
                red_format = workbook.add_format({'bg_color': '#FF9999', 'align': 'center', 'valign': 'vcenter'})


                worksheet = workbook.add_worksheet(invoice.name[:31])

                # Add a note if this picking is a backorder
                worksheet.write(0, 1, 'Facture ' + invoice.name , header_format)
                worksheet.write(0, 2, 'Total :', header_format)
                worksheet.write(0, 3, invoice.amount_total , header_format)

                # Headers
                headers = ['EAN', 'Description', 'Q', 'BL', 'PV TTC', 'TVA', 'PV HTC', 'Remise 1', 'Remise 2', 'Prix Net', 'Total HTC',
                           'Date de parution', 'Auteur', 'Editeur', 'Collection']
                worksheet.set_row(1, 30)  # Header row height

                for col, header in enumerate(headers):
                    worksheet.write(1, col, header, header_format)

                # Set column widths
                column_widths = [45, 10, 15, 8, 12, 25, 17, 25, 15, 20]
                for col, width in enumerate(column_widths):
                    worksheet.set_column(col, col, width)

                row = 2
                for line in invoice.line_ids.filtered(lambda l: l.product_id):

                    product = line.product_id
                    product_template = product.product_tmpl_id

                    # Retrieve the tax rate from the product's associated taxes
                    tax_rate = 1.0  # Default to 1 (no tax) if no tax is found
                    tax_name = ''
                    if product.taxes_id:
                        # Assuming the first tax is the primary one to apply; you may need to adjust if multiple taxes exist
                        primary_tax = product.taxes_id[0]
                        tax_rate = 1 + (primary_tax.amount / 100)
                        tax_name = primary_tax.name
                    # Add Barcode as Image and Numeric Value
                    if product.barcode:
                        # Numeric barcode value
                        worksheet.write(row, 0, product.barcode, center_format)
                    # Write basic details with dynamic tax rate
                    worksheet.write(row, 1, product.display_name, center_format)
                    worksheet.write(row, 2, line.quantity, center_format)
                    if len(line.sale_line_ids.move_ids) == 1:
                        worksheet.write(row, 3, str(line.sale_line_ids.move_ids.picking_id[0].mapped('name')), center_format)
                    elif len(line.sale_line_ids.move_ids) > 1:
                        worksheet.write(row, 3, str(line.sale_line_ids.move_ids.picking_id.mapped('name')), center_format)
                    else:
                        worksheet.write(row, 3, '', center_format)
                    worksheet.write(row, 4, round(product.list_price), center_format)
                    worksheet.write(row, 5, tax_name, center_format)
                    worksheet.write(row, 6, round(product.list_price / tax_rate,2), center_format)
                    worksheet.write(row, 7, line.discount_primary, center_format)
                    worksheet.write(row, 8, line.discount_secondary, center_format)
                    worksheet.write(row, 9, line.price_subtotal, center_format)
                    worksheet.write(row, 10, line.price_total, center_format)


                    if product_template.date_parution:
                        worksheet.write(row, 11, product_template.date_parution.strftime('%d/%m/%Y') or "", center_format)
                    # Write Author, Publisher, Collection information with conditional format
                    worksheet.write(row, 12, product_template.auteur or "", center_format)
                    worksheet.write(row, 13, product_template.editeur or "", center_format)
                    worksheet.write(row, 14, product_template.collection or "", center_format)

                    row += 1

                workbook.close()

                # Prepare response
                output.seek(0)
                filename = f"Invoice_{invoice.name}_{invoice.invoice_date.strftime('%Y%m%d')}.xlsx"
                headers = [
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename={filename}'),
                ]
                return request.make_response(output.read(), headers=headers)

            else:
                return request.not_found()
        else:
            return request.not_found()


    @http.route(['/nos-editeurs',
                 '/nos-editeurs/page/<int:page>'], type='http', auth="user", website=True)
    def editeur_page(self, search=None, page=1, limit=30, **post):
        cr = request.env.cr
        offset = (page - 1) * limit

        website = request.env['website'].get_current_website()

        # Use parameterized query to avoid SQL injection, and ensure proper indexing on the queried columns
        search_query = ""
        params = []

        if search:
            search_query = "WHERE LOWER(editeur) ILIKE %s"
            params.append(f'%{search}%')

            # Fetch data from mv_editeur with pagination
            sql = f"""
                SELECT * FROM mv_editeur
                {search_query}
                LIMIT %s OFFSET %s;
            """

        # Fetch data from mv_editeur with pagination
        sql = f"""
            SELECT * FROM mv_editeur
            LIMIT %s OFFSET %s;
        """
        params.extend([limit, offset])  # Add limit and offset to params
        cr.execute(sql, params)
        results = cr.dictfetchall()

        # Transform results into JSON format
        editors_json = [{'id': editor['product_template_id'], 'name': editor['editeur']} for editor in results]

        # Fetch total count from mv_editeur_count
        count_sql = f"""
            SELECT SUM(editor_count) FROM mv_editeur_count
            {search_query};
        """

        count_params = [f'%{search}%'] if search else []
        cr.execute(count_sql, count_params)
        total = cr.fetchone()[0]

        # Optimize pager calculation
        url = '/nos-editeurs'
        if search:
            post['search'] = search
        pager_data = website.pager(url=url, total=total, page=page, step=limit)

        return request.render('net_diffusion.editor_page_template', {
            'editors_json': editors_json,
            'pager': pager_data,
            'search': search,
        })

    @http.route(['/get/tags_editor'], type='json', auth="public", website=True)
    def get_tags_editor(self, search=None, **post):
        Tag = request.env['product.tag']
        editors_json = []
        if search:
            editors = Tag.search([('name', 'ilike', search), ('categ_id', '=', 1)], limit=30)
            for editor in editors:
                editors_json.append({
                    'id': editor.id,
                    'name': editor.name,
                })
        else:
            editors = Tag.search([('categ_id', '=', 1)], limit=30)
            for editor in editors:
                editors_json.append({
                    'id': editor.id,
                    'name': editor.name,
                })
        return editors_json

    @http.route(['/get/tags_collection'], type='json', auth="public", website=True)
    def get_tags_collection(self, search=None, **post):
        Tag = request.env['product.tag']
        collections_json = []
        if search:
            collections = Tag.search([('name', 'ilike', search), ('categ_id', '=', 3)], limit=30)
            for collection in collections:
                collections_json.append({
                    'id': collection.id,
                    'name': collection.name,
                })
        else:
            collections = Tag.search([('categ_id', '=', 3)], limit=30)
            for collection in collections:
                collections_json.append({
                    'id': collection.id,
                    'name': collection.name,
                })
        return collections_json

    @http.route(['/get/tags_author'], type='json', auth="public", website=True)
    def get_tags_author(self, search=None, **post):
        Tag = request.env['product.tag']
        authors_json = []
        if search:
            authors = Tag.search([('name', 'ilike', search), ('categ_id', '=', 2)], limit=30)
            for author in authors:
                authors_json.append({
                    'id': author.id,
                    'name': author.name,
                })
        else:
            authors = Tag.search([('categ_id', '=', 1)], limit=30)
            for author in authors:
                authors_json.append({
                    'id': author.id,
                    'name': author.name,
                })
        return authors_json

    @http.route(['/shop/cart_fast'], type='http', auth="user", website=True)
    def cart_fast(self, **post):

        order = request.website.sale_get_order()

        values = {
            'order': order,
            'website_sale_order': order,
        }
        if order and order.carrier_id:
            # Express checkout is based on the amout of the sale order. If there is already a
            # delivery line, Express Checkout form will display and compute the price of the
            # delivery two times (One already computed in the total amount of the SO and one added
            # in the form while selecting the delivery carrier)
            order._remove_delivery_line()
        if order:
            order.order_line.filtered(lambda l: not l.product_id.active).unlink()
            values['suggested_products'] = order._cart_accessories()
            values.update(self._get_express_shop_payment_values(order))

        values.update(self._cart_values(**post))
        return request.render('net_diffusion.cart_fast_template', values)

    @http.route(['/shop/add_product'], type='http', auth="public", website=True)
    def cart_add_product(self, **post):
        product_list = post.get('product_reference')

        order = request.website.sale_get_order(force_create=True)
        ean_notfound = []
        for product_reference in product_list.split(' '):
            product = request.env['product.product'].search([('barcode', '=', product_reference)], limit=1)
            if product:
                order._cart_update(
                    product_id=product.id,
                    add_qty=1,
                )
            else:
                ean_notfound.append(product_reference)

        values = {
            'order': order,
            'website_sale_order': order,
            'ean_notfound': ean_notfound
        }
        if order:
            order.order_line.filtered(lambda l: not l.product_id.active).unlink()
            values['suggested_products'] = order._cart_accessories()
            values.update(self._get_express_shop_payment_values(order))

        values.update(self._cart_values(**post))
        return self.cart_fast()

    @http.route(['/get/total_order'], type='json', auth="public", website=True)
    def get_total_order(self, **post):
        # Get the current website sale order (cart)
        order = request.website.sale_get_order()

        # Initialize the return value as an empty dictionary
        value = {}

        if order:
            # Get the total order amount, taxes, and other related details
            value = {
                'order_id': order.id,
                'amount_total': order.amount_total,  # Total order amount
                'amount_tax': order.amount_tax,  # Total taxes applied
                'amount_untaxed': order.amount_untaxed,  # Untaxed amount
                'currency': order.currency_id.name,  # Currency used in the order
                'order_lines': order.order_line.mapped(lambda line: {
                    'name': line.name,
                    'price_unit': line.price_unit,
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'subtotal': line.price_subtotal,
                })
            }

        # Return the order details or an empty dict if no order exists
        return value


    @http.route(['/catalogue'], type='http', auth="user", website=True)
    def catalogue_page(self):
        disponibilities = request.env['dr.product.label'].search([])

        return request.render('net_diffusion.catalogue_page_template', {
            'disponibilities': disponibilities,
        })

    @http.route(['/catalogue-ajax'], type='json', auth="user", website=True)
    def catalogue_page_ajax(self, search=None, page=1, limit=50, **post):
        cr = request.env.cr
        url = '/catalogue'
        website = request.env['website'].get_current_website()
        pricelist = request.env.user.partner_id.property_product_pricelist
        if not pricelist:
            pricelist = website.pricelist_id
        # Use parameterized query to avoid SQL injection, and ensure proper indexing on the queried columns
        search_query = ""
        params = []
        search_domain = [('active', '=', True),('website_published', '=', True)]
        if post['title']:
            search_domain += [('name', 'ilike', post['title'])]
        if post['editeur']:
            search_domain += [('editeur', 'ilike', post['editeur'])]
        if post['auteur']:
            search_domain += [('auteur', 'ilike', post['auteur'])]
        if post['collection']:
            search_domain += [('collection', 'ilike', post['collection'])]
        if post['ean']:
            search_domain += [('barcode', 'ilike', post['ean'])]
        if post['disponibility']:
            search_domain += [('dr_label_id', 'ilike', int(post['disponibility']))]

        products = request.env['product.template'].search(search_domain, limit=50)
        products_count = request.env['product.template'].search_count(search_domain, limit=50)
        pager_data = website.pager(url=url, total=products_count, page=page, step=limit)
        offset = pager_data['offset']
        products = products[offset:offset + limit]
        products_data = []

        for product in products:
            product_variant = request.env['product.product'].search([('product_tmpl_id', '=', product.id)], limit=1)
            product_price = pricelist._price_get(
                product,
                1).get(1)
            products_data.append({
                'id': product.id,
                'variant': product_variant.id if product_variant else None,
                'name': product.name,
                'website_url': product.website_url,
                'editeur': product.editeur,
                'auteur': product.auteur,
                'barcode': product.barcode,
                'collection': product.collection,
                'price': product_price,
                'base_price': product.list_price,
                'description_ecommerce': product.description_ecommerce,
                'type_livre': product.type_livre,
                'date_parution': product.date_parution.strftime('%d/%m/%Y'),
                'dilicom_url': product.dilicom_url,
                'token': product.dilicom_url,
                'csrf_token': request.csrf_token(),
                'disponibility_name': product.dr_label_id.name,
                'disponibility_color': product.dr_label_id.text_color,
                'disponibility_color_bck': product.dr_label_id.background_color,
            })
        return products_data