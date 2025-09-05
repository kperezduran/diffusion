import csv
import io
import base64
import xlsxwriter
from odoo import models, fields, api

class SaleReportWizard(models.TransientModel):
    _name = 'sale.report.wizard2'
    _description = 'Sales or Credit Note Report Wizard'

    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)
    report_type = fields.Selection([
        ('vente', 'Vente'),
        ('credit_note', 'Credit Note')
    ], string="Report Type", required=True)
    fichier = fields.Binary(string="Generated Excel File")
    filename = fields.Char(string="File Name")

    def action_generate_report(self):
        self.ensure_one()

        journal_id = 1 if self.report_type == 'vente' else 10
        move_type = 'out_invoice' if self.report_type == 'vente' else 'out_refund'

        query = """
        SELECT pp.barcode,
               CASE WHEN pt.name ->> 'fr_FR' IS NOT NULL THEN pt.name ->> 'fr_FR'
                    ELSE pt.name ->> 'en_US' END AS product_name,
               pt.editeur,
               rp.name AS supplier_name,
               SUM(aml.quantity) AS total_qty_invoiced,
               pt.list_price
        FROM account_move_line AS aml
        INNER JOIN account_move AS am ON am.id = aml.move_id
        INNER JOIN product_product AS pp ON aml.product_id = pp.id
        INNER JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
        LEFT JOIN LATERAL (
            SELECT rp_sub.*
            FROM product_supplierinfo AS psi_sub
            INNER JOIN res_partner AS rp_sub ON rp_sub.id = psi_sub.partner_id
            WHERE psi_sub.product_tmpl_id = pt.id
            ORDER BY rp_sub.id DESC
            LIMIT 1
        ) AS rp ON TRUE
        WHERE aml.quantity > 0
          AND am.invoice_date BETWEEN %s AND %s
          AND am.journal_id = %s
          AND am.state = 'posted'
          AND am.move_type = %s
        GROUP BY pp.barcode, pt.name, pt.editeur, rp.name, pt.list_price
    """
        params = (self.date_start, self.date_end, journal_id, move_type)
        self.env.cr.execute(query, params)
        rows = self.env.cr.fetchall()

        headers = [
            'Barcode',
            'Product Name',
            'Editor',
            'Supplier Name',
            'Total Qty Invoiced',
            'List Price'
        ]

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Sales Report")

        # Write headers
        worksheet.write_row(0, 0, headers)

        # Write data (strings as strings, numbers as numbers)
        for r, row in enumerate(rows, start=1):
            barcode, product_name, editeur, supplier_name, total_qty_invoiced, list_price = row
            worksheet.write_string(r, 0, barcode or "")
            worksheet.write_string(r, 1, product_name or "")
            worksheet.write_string(r, 2, editeur or "")
            worksheet.write_string(r, 3, supplier_name or "")
            worksheet.write_number(r, 4, float(total_qty_invoiced or 0))
            worksheet.write_number(r, 5, float(list_price or 0))

        workbook.close()
        output.seek(0)
        data = output.getvalue()

        self.fichier = base64.b64encode(data)
        self.filename = f"report_{self.report_type}_{self.date_start}_{self.date_end}.xlsx"

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.report.wizard2',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

class InvoiceUpdate(models.TransientModel):
    _name = 'account.compute_update'
    _description = 'Run Update Manually'

    # def _update_sale_order_draft(self):
    #     # As this function is in a new thread, I need to open a new cursor, because the old one may be closed
    #     with self.pool.cursor() as new_cr:
    #         self = self.with_env(self.env(cr=new_cr))
    #         scheduler_cron = self.sudo().env.ref('stock.ir_cron_scheduler_action')
    #         # Avoid to run the scheduler multiple times in the same time
    #         try:
    #             with tools.mute_logger('odoo.sql_db'):
    #                 self._cr.execute("SELECT id FROM ir_cron WHERE id = %s FOR UPDATE NOWAIT", (scheduler_cron.id,))
    #         except Exception:
    #             _logger.info('Attempt to run procurement scheduler aborted, as already running')
    #             self._cr.rollback()
    #             return {}
    #
    #         for company in self.env.user.company_ids:
    #             cids = (self.env.user.company_id | self.env.user.company_ids).ids
    #             self.env['procurement.group'].with_context(allowed_company_ids=cids).run_scheduler(
    #                 use_new_cursor=self._cr.dbname,
    #                 company_id=company.id)
    #         self._cr.rollback()
    #     return {}
    # def _update_sale_order_draft(self):
    #     orders_to_update = self.env['sale.order'].search([('state', '=', 'draft')])
    #     for order in orders_to_update:
    #         for line in order.order_line:
    #             # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
    #             # manually edited
    #             if line.qty_invoiced > 0 or (line.product_id.expense_policy == 'cost' and line.is_expense):
    #                 continue
    #             if not line.product_uom or not line.product_id:
    #                 line.price_unit = 0.0
    #             else:
    #                 line = line.with_company(line.company_id)
    #                 price = line._get_display_price()
    #                 line.price_unit = line.product_id._get_tax_included_unit_price(
    #                     line.company_id or line.env.company,
    #                     line.order_id.currency_id,
    #                     line.order_id.date_order,
    #                     'sale',
    #                     fiscal_position=line.order_id.fiscal_position_id,
    #                     product_price_unit=price,
    #                     product_currency=line.currency_id
    #                 )
    #     return {}

    def update_invoice(self):
        cr = self.env.cr
        # Fetch data from mv_editeur with pagination
        sql = f"""
                        SELECT sol.id FROM account_move_line AS sol
                                   INNER JOIN account_move AS so ON sol.move_id = so.id
                                   INNER JOIN product_product AS pp ON sol.product_id = pp.id
                                   INNER JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
            WHERE sol.price_unit != pt.list_price
              AND so.state = 'draft';

        """
        cr.execute(sql)
        results = cr.dictfetchall()
        line_ids = [r['id'] for r in results]
        lines_to_update = self.env['account.move.line'].browse(line_ids)

        for line in lines_to_update:
            if line.move_id.state == 'draft':
                # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
                # manually edited
                if not line.product_uom or not line.product_id:
                    line.price_unit = 0.0
                else:
                    line = line.with_company(line.company_id)
                    price = line._get_display_price()
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                        line.company_id or line.env.company,
                        line.move_id.currency_id,
                        line.move_id.date_order,
                        'sale',
                        fiscal_position=line.move_id.fiscal_position_id,
                        product_price_unit=price,
                        product_currency=line.currency_id
                    )

        return {'type': 'ir.actions.client', 'tag': 'reload'}
# optional, for download UI

    # def action_generate_report(self):
    #     self.ensure_one()
    #     query = """
    #         SELECT pp.barcode,
    #                CASE WHEN pt.name ->> 'fr_FR' IS NOT NULL THEN pt.name ->> 'fr_FR'
    #                     ELSE pt.name ->> 'en_US' END AS product_name,
    #                pt.editeur,
    #                rp.name AS supplier_name,
    #                SUM(aml.quantity) AS total_qty_invoiced,
    #                pt.list_price
    #         FROM account_move_line AS aml
    #         INNER JOIN account_move AS am ON am.id = aml.move_id
    #         INNER JOIN product_product AS pp ON aml.product_id = pp.id
    #         INNER JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
    #         LEFT JOIN LATERAL (
    #             SELECT rp_sub.*
    #             FROM product_supplierinfo AS psi_sub
    #             INNER JOIN res_partner AS rp_sub ON rp_sub.id = psi_sub.partner_id
    #             WHERE psi_sub.product_tmpl_id = pt.id
    #             ORDER BY rp_sub.id DESC
    #             LIMIT 1
    #         ) AS rp ON TRUE
    #         WHERE aml.quantity > 0
    #           AND am.invoice_date BETWEEN %s AND %s
    #           AND am.journal_id = %s
    #           AND am.state = 'posted'
    #           AND am.move_type = %s
    #         GROUP BY pp.barcode, pt.name, pt.editeur, rp.name, pt.list_price
    #     """
    #
    #     journal_id = 1 if self.report_type == 'vente' else 10
    #     move_type = 'out_invoice' if self.report_type == 'vente' else 'out_refund'
    #
    #     self.env.cr.execute(query, (
    #         self.date_start,
    #         self.date_end,
    #         journal_id,
    #         move_type
    #     ))
    #     rows = self.env.cr.fetchall()
    #     columns = [desc[0] for desc in self.env.cr.description]
    #
    #     output = io.BytesIO()
    #     # Use constant_memory for large data sets
    #     workbook = xlsxwriter.Workbook(output, {'constant_memory': True})
    #     worksheet = workbook.add_worksheet("Sales Report")
    #
    #     # Write headers in a single call
    #     worksheet.write_row(0, 0, columns)
    #
    #     # Write data rows efficiently
    #     for row_num, row_data in enumerate(rows, start=1):
    #         worksheet.write_row(row_num, 0, row_data)
    #
    #     workbook.close()
    #     output.seek(0)
    #
    #     self.fichier = base64.b64encode(output.read())
    #     self.filename = f"report_{self.report_type}_{self.date_start}_{self.date_end}.xlsx"
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'sale.report.wizard2',
    #         'view_mode': 'form',
    #         'res_id': self.id,
    #         'target': 'new',
    #     }
