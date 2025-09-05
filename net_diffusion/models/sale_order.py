# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero
from odoo.tools.sql import SQL
from bisect import bisect_left
from collections import defaultdict
import re
from odoo.http import request, content_disposition
from odoo.tools import float_is_zero, float_compare, float_round, format_date, groupby

from datetime import datetime
import xlsxwriter
import io

from odoo import models, fields, api
import xlsxwriter
import io
import base64
from datetime import datetime


class SaleOrderXlsxWizard(models.TransientModel):
    _name = 'sale.order.xlsx.wizard'
    _description = 'Download Sale Order XLSX'

    file_name = fields.Char(string='File Name')
    file_data = fields.Binary(string='File', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(SaleOrderXlsxWizard, self).default_get(fields_list)
        sale_order_id = self.env.context.get('active_id')
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id)

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet(sale_order.name)

            # Define formats
            header_format = workbook.add_format({'bold': True, 'align': 'center'})
            center_format = workbook.add_format({'align': 'center'})

            # Add headers
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
            for line in sale_order.order_line:
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
                worksheet.write(row, 1, round(product.list_price / tax_rate, 2), center_format)
                worksheet.write(row, 2, product.list_price, center_format)
                worksheet.write(row, 3, line.product_uom_qty, center_format)
                worksheet.write(row, 4, line.qty_delivered, center_format)

                # Check if delivered quantity is less than ordered
                format_to_use = center_format if line.qty_delivered < line.product_uom_qty else center_format

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
            output.seek(0)

            # Convert to base64
            file_content = base64.b64encode(output.read())
            file_name = f"Sale_Order_{sale_order.name}_{datetime.now().strftime('%Y%m%d')}.xlsx"

            res.update({
                'file_name': file_name,
                'file_data': file_content
            })
        return res

    def download_file(self):
        """ Trigger download of the generated file. """
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{self._name}/{self.id}/file_data/{self.file_name}?download=true",
            'target': 'self',
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    date_parution = fields.Date(compute='_compute_infos_line')
    supplier = fields.Many2one("res.partner", compute='_compute_infos_line', string="Fournisseur")
    editeur = fields.Char(string="Editeur", related="product_id.product_tmpl_id.editeur")
    barcode = fields.Char(string="EAN", related="product_id.barcode")
    code_dispo = fields.Char(string="Dispo", related="product_id.product_tmpl_id.code_disponibility")
    discount_primary = fields.Float(string="Remise 1", default=lambda self: self.discount)
    discount_secondary = fields.Float(string="Remise 2")
    import_state = fields.Boolean(string='Créer en import', related="product_id.import_state")

    def _compute_infos_line(self):
        for record in self:
            if record.product_id:
                record.date_parution = record.product_id.product_tmpl_id.date_parution
                if record.product_id.variant_seller_ids:
                    record.supplier = record.product_id.variant_seller_ids[0].partner_id.id
                else:
                    record.supplier = None
            else:
                record.date_parution = None
                record.supplier = None

    @api.onchange('product_id')
    def _onchange_product_id_diffusion(self):
        """Set discount_primary to the same value as discount when the product changes."""
        for line in self:
            if line.discount_primary == 0:  # Avoid overwriting if already set
                line.discount_primary = line.discount

    @api.onchange('discount_primary', 'discount_secondary')
    def _onchange_discount(self):
        for line in self:
            if line.discount_primary or line.discount_secondary:
                discount = 100 * ((100 - line.discount_primary) / 100) * ((100 - line.discount_secondary) / 100)
                line.discount = 100 - discount
            else:
                line.discount = line.discount_primary  # Default to primary if no secondary

    # @api.depends('product_id')
    # def _compute_name(self):
    #     for line in self:
    #         if not line.product_id:
    #             continue
    #         lang = line.order_id._get_lang()
    #         if lang != self.env.lang:
    #             line = line.with_context(lang=lang)
    #         name = line._get_sale_order_line_multiline_description_sale()
    #         if line.is_downpayment and not line.display_type:
    #             context = {'lang': lang}
    #             dp_state = line._get_downpayment_state()
    #             if dp_state == 'draft':
    #                 name = _("%(line_description)s (Draft)", line_description=name)
    #             elif dp_state == 'cancel':
    #                 name = _("%(line_description)s (Canceled)", line_description=name)
    #             else:
    #                 invoice = line._get_invoice_lines().move_id
    #                 if len(invoice) == 1 and invoice.payment_reference and invoice.invoice_date:
    #                     name = _(
    #                         "%(line_description)s (ref: %(reference)s on %(date)s)",
    #                         line_description=name,
    #                         reference=invoice.payment_reference,
    #                         date=format_date(line.env, invoice.invoice_date),
    #                     )
    #             del context
    #         if ']' in name:
    #             line.name = name.split('] ')[1]
    #         else:
    #             line.name = name


class AccountMove(models.Model):
    _inherit = "sale.order"

    total_qty = fields.Integer(compute='_compute_total_qty', string="Total articles")
    purchase_order_ids = fields.One2many('purchase.order', 'sale_order_id', string="Commandes Fournisseur")
    is_dedie = fields.Boolean(string="Commande dédié", compute='_compute_dedie_status')
    dedie_status = fields.Selection(
        selection=[
            ('0', ''),
            ('1', 'A traiter'),
            ('2', 'Traitement finis'),
            ],
        string="status dédié", compute='_compute_dedie_status'
    )

    def _compute_dedie_status(self):
        for sale in self:
            if len(sale.purchase_order_ids) > 0:
                sale.is_dedie = True
                sale.dedie_status = '2'
                for purchase in sale.purchase_order_ids:
                    if purchase.state != 'purchase':
                        sale.dedie_status = '1'

            else:
                sale.dedie_status = '0'
                sale.is_dedie = False

    def action_confirm_drop(self):
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm cancelled SO's
        """
        if self.state == 'sale':
            self.write({'state': 'draft'})
        if not all(order._can_be_confirmed() for order in self):
            raise UserError(_(
                "The following orders are not in a state requiring confirmation: %s",
                ", ".join(self.mapped('display_name')),
            ))


        self.order_line._validate_analytic_distribution()

        for order in self:
            order.validate_taxes_on_sales_order()
            if order.partner_id in order.message_partner_ids:
                continue
            order.message_subscribe([order.partner_id.id])

        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self[:1].create_uid.has_group('sale.group_auto_done_setting'):
            # Public user can confirm SO, so we check the group on any record creator.
            self.action_lock()

        suppliers_data = []
        added_supplier_ids = {}  # Dictionary to track suppliers and their order lines

        for line in self.order_line:
            product = line.product_id.product_tmpl_id
            if product.seller_ids:  # Ensure the product has suppliers
                supplier = product.seller_ids[0]  # Get the first supplier

                if supplier.partner_id.id not in added_supplier_ids:
                    # Add new supplier with the first order line
                    added_supplier_ids[supplier.partner_id.id] = {
                        'supplier': supplier,
                        'order_lines': [line]
                    }
                    suppliers_data.append(added_supplier_ids[supplier.partner_id.id])
                else:
                    # Append the order line to the existing supplier entry
                    added_supplier_ids[supplier.partner_id.id]['order_lines'].append(line)

        purchase_orders = {}  # Dictionary to group PO by supplier

        for line in suppliers_data:
            supplier_id = line.get('supplier').partner_id.id

            # Check if a purchase order for this supplier already exists
            if supplier_id not in purchase_orders:
                purchase_orders[supplier_id] = self.env['purchase.order'].create({
                    'partner_id': supplier_id,
                    'sale_order_id': self.id,
                    'state': 'drop',  # Custom state 'drop'
                    'date_order': fields.Datetime.now(),  # Set current date
                    'order_line': []  # Empty list, will be filled later
                })

            purchase_order = purchase_orders[supplier_id]
            for sale_line in line.get('order_lines'):
                # Create a purchase order line
                self.env['purchase.order.line'].create({
                    'order_id': purchase_order.id,
                    'product_id': sale_line.product_id.id,
                    'name': sale_line.name,
                    'product_qty': sale_line.product_uom_qty,
                    'product_uom': sale_line.product_uom.id,
                    'date_planned': fields.Datetime.now(),  # Set planned date
                })

        return True

    def download_picking_xlsx(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Download XLSX',
            'res_model': 'sale.order.xlsx.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
            },
        }

    # def download_picking_xlsx(self):
    #     for sale_order in self:
    #
    #         # Generate Excel file
    #         output = io.BytesIO()
    #         workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    #
    #         # Define formats
    #         header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
    #         center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
    #         red_format = workbook.add_format({'bg_color': '#FF9999', 'align': 'center', 'valign': 'vcenter'})
    #
    #         worksheet = workbook.add_worksheet(sale_order.name)
    #
    #         # Add a note if this picking is a backorder
    #         worksheet.write(0, 0, 'Commande', header_format)
    #
    #         # Headers
    #         headers = ['Produit', 'HTVA', 'TTC', 'Quantités', 'Quantités livrés',
    #                    'Barcode (Image)', 'Barcode (Numéro)', 'Date de parution', 'Auteur', 'Editeur', 'Collection']
    #         worksheet.set_row(1, 30)  # Header row height
    #
    #         for col, header in enumerate(headers):
    #             worksheet.write(1, col, header, header_format)
    #
    #         # Set column widths
    #         column_widths = [45, 10, 15, 8, 12, 25, 17, 25, 15, 20]
    #         for col, width in enumerate(column_widths):
    #             worksheet.set_column(col, col, width)
    #
    #         row = 2
    #         for line in sale_order.order_line:
    #             product = line.product_id
    #             product_template = product.product_tmpl_id
    #
    #             # Retrieve the tax rate from the product's associated taxes
    #             tax_rate = 1.0  # Default to 1 (no tax) if no tax is found
    #             if product.taxes_id:
    #                 # Assuming the first tax is the primary one to apply; you may need to adjust if multiple taxes exist
    #                 primary_tax = product.taxes_id[0]
    #                 tax_rate = 1 + (primary_tax.amount / 100)
    #
    #             # Write basic details with dynamic tax rate
    #             worksheet.write(row, 0, product.display_name, center_format)
    #             worksheet.write(row, 1, round(product.list_price / tax_rate, 2), center_format)
    #             worksheet.write(row, 2, product.list_price, center_format)
    #             worksheet.write(row, 3, line.product_uom_qty, center_format)
    #             worksheet.write(row, 4, line.qty_delivered, center_format)
    #
    #             # Check if delivered quantity is less than ordered
    #             format_to_use = center_format if line.qty_delivered < line.product_uom_qty else center_format
    #
    #             # Add Barcode as Image and Numeric Value
    #             if product.barcode:
    #                 # Numeric barcode value
    #                 worksheet.write(row, 6, product.barcode, center_format)
    #
    #                 # Generate Barcode Image
    #                 barcode_img = self.env['ir.actions.report'].barcode(
    #                     'EAN13', product.barcode, width=300, height=100
    #                 )
    #                 image_data = io.BytesIO(barcode_img)
    #
    #                 # Set row height to 52px for barcode rows only
    #                 worksheet.set_row(row, 52)
    #
    #                 # Insert image
    #                 worksheet.insert_image(row, 5, 'barcode.png',
    #                                        {'image_data': image_data, 'x_scale': 0.5, 'y_scale': 0.5})
    #             if product_template.date_parution:
    #                 worksheet.write(row, 7, product_template.date_parution.strftime('%d/%m/%Y') or "", format_to_use)
    #             # Write Author, Publisher, Collection information with conditional format
    #             worksheet.write(row, 8, product_template.auteur or "", format_to_use)
    #             worksheet.write(row, 9, product_template.editeur or "", format_to_use)
    #             worksheet.write(row, 10, product_template.collection or "", format_to_use)
    #
    #             row += 1
    #
    #     workbook.close()
    #
    #     # Prepare response
    #     output.seek(0)
    #     filename = f"Picking_List_{sale_order.name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    #     headers = [
    #         ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    #         ('Content-Disposition', f'attachment; filename={filename}'),
    #     ]
    #     return request.make_response(
    #         output.read(),
    #         headers=[
    #             ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    #             ('Content-Disposition', content_disposition(filename))
    #         ]
    #     )

    def _compute_total_qty(self):
        for record in self:
            qty = 0
            if record.order_line:
                for line in record.order_line:
                    qty += line.product_qty
            record.total_qty = qty

    def open_import_xls(self):
        return {
            'name': _("Importer fichier XLSX"),
            'view_mode': 'form',
            'views': [(self.env.ref('net_diffusion.import_order_wizard_form_xls').id, 'form')],
            'res_model': 'wizard.import_xlsx_order',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [],
            'context': {
                'default_sale_order_id': self.id,
            },
        }

    def open_import_ods(self):
        return {
            'name': _("Importer fichier ODS"),
            'view_mode': 'form',
            'views': [(self.env.ref('net_diffusion.import_order_wizard_form_ods').id, 'form')],
            'res_model': 'wizard.import_xlsx_order',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [],
            'context': {
                'default_sale_order_id': self.id,
            },
        }
