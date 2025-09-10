import csv
import io
import base64
import xlsxwriter
from odoo import models, fields, api

class InvoiceUpdate(models.TransientModel):
    _name = 'account.compute_update'
    _description = 'Run Update Manually'

    def update_invoice(self):
        cr = self.env.cr
        # Fetch data from mv_editeur with pagination
        sql = f"""
                        SELECT sol.id FROM account_move_line AS sol
                                   INNER JOIN account_move AS so ON sol.move_id = so.id
                                   INNER JOIN product_product AS pp ON sol.product_id = pp.id
                                   INNER JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
            WHERE sol.price_unit != pt.list_price and so.journal_id = 1 and so.move_type = 'out_invoice' and pt.id not in (4,1586894,1411678,1411679,1411680)
              AND so.id = 21016 AND so.state = 'draft';
        """
        cr.execute(sql)
        results = cr.dictfetchall()
        line_ids = [r['id'] for r in results]
        lines_to_update = self.env['account.move.line'].browse(line_ids)

        for line in lines_to_update:
            if line.move_id.state == 'draft':
                # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
                # manually edited
                line = line.with_company(line.company_id)
                price = line.product_id.list_price
                line.price_unit = line.product_id._get_tax_included_unit_price(
                    line.company_id or line.env.company,
                    line.move_id.currency_id,
                    line.move_id.invoice_date,
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
