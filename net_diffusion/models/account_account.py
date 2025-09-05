# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from datetime import datetime, timedelta
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero
from odoo.tools.sql import SQL
from bisect import bisect_left
from collections import defaultdict
import re
import xlsxwriter
import os


class AccountJournal(models.Model):
    _inherit = "account.journal"

    url_download = fields.Char(string='Stock Rapport Téléchargment', compute='_compute_url')
    type_report = fields.Selection(
        selection=[
            ('out_invoice', 'Facture Client'),
            ('out_refund', 'Avoir Client'),
            ('in_invoice', 'Facture Fournisseur'),
            ('in_refund', 'Avoir Fournisseur'),
        ],
        string="Facture type", default='out_invoice')
    code_bob = fields.Char(string='Code BOB')
    report_date_from = fields.Date(string='Rapport date_debut')
    report_date_to = fields.Date(string='Rapport date_fin')

    def _compute_url(self):
        for journal in self:
            if journal.type_report and journal.report_date_from and journal.report_date_to and journal.code_bob:
                cr = self.env.cr
                filename = f"LKSLS_{journal.type_report}_{journal.name}_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}"
                file_path = f"/opt/odoo/addons/website_sale/static/description/{filename}.xlsx"
                if journal.type_report in ('out_invoice', 'in_invoice'):
                    DAYBOOKTYPE = 'F'
                else:
                    DAYBOOKTYPE = 'NC'
                sql = f"""
                    WITH OrderedLines AS (
                        SELECT
                            aml.id AS move_line_id,
                            am.id AS move_id,
                            aml.account_id AS account_id,
                            ROW_NUMBER() OVER (PARTITION BY am.id ORDER BY aml.id) AS new_sequence
                        FROM account_move_line aml
                        INNER JOIN account_move am ON aml.move_id = am.id
                        WHERE am.state = 'posted'
                          AND am.move_type = '{journal.type_report}'
                          AND am.journal_id = {journal.id}
                    )
                    SELECT
                        '{journal.code_bob}' AS "DAYBOOK",
                        '{DAYBOOKTYPE}' AS "DAYBOOKTYPE",
                        CAST(TO_CHAR(am.invoice_date, 'MM') AS integer) AS "ACC_MONTH",
                        CAST(TO_CHAR(am.invoice_date, 'YYYY') AS integer) AS "ACC_YEAR",
                        TO_CHAR(am.invoice_date, 'DD/MM/YYYY') AS "DATE",
                        TO_CHAR(am.invoice_date_due, 'DD/MM/YYYY') AS "DUEDATE",
                        REPLACE(am.name, '/', '') AS "NUMBER",
                        rp.bob_ref AS "THPARTY",
                        am.payment_reference AS "INTERNAL_COMMENT",
                        LEFT(rp.name, 40) AS "EXTERNAL_COMMENT",
                        REGEXP_REPLACE(am.payment_reference, '[+/]', '', 'g') AS "BOBVCS",
                        am.amount_total AS "EURO_AMOUNT",
                        '' AS "LIBIMP0",
                        aa.code AS "LEDGER_ACCOUNT0",
                        SUM(aml.balance) AS "BASE_AMOUNT0",
                        COALESCE(tax_data.tax_names, '') AS "TAX_CODE0",
                        SUM(aml.price_total) - SUM(aml.price_subtotal) AS "TAX_AMOUNT0",
                        '' AS "ANA1IMP0",
                        '' AS "ANA2IMP0",
                        '' AS "PDF"
                    FROM account_move am
                    INNER JOIN account_move_line aml ON am.id = aml.move_id
                    INNER JOIN OrderedLines ON aml.id = OrderedLines.move_line_id
                    INNER JOIN product_product pp ON aml.product_id = pp.id
                    INNER JOIN account_journal aj ON aj.id = am.journal_id
                    INNER JOIN res_partner rp ON rp.id = am.partner_id
                    INNER JOIN account_account aa ON aa.id = aml.account_id
                    INNER JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN LATERAL (
                        SELECT
                            CASE
                                WHEN at.id = 16 THEN '6% M'
                                WHEN at.id = 11 THEN 'ESTRF0'
                                WHEN at.id = 8 THEN 'ESTRF0'
                                WHEN at.id = 74 THEN 'NSS  6'
                                WHEN at.id = 72 THEN '21%'
                                WHEN at.id = 6 THEN 'NSS  6'
                                ELSE STRING_AGG(at.name->>'fr_FR', ', ')
                            END AS tax_names
                        FROM account_move_line_account_tax_rel amlat
                        INNER JOIN account_tax at ON amlat.account_tax_id = at.id
                        WHERE amlat.account_move_line_id = aml.id
                        GROUP BY at.id
                    ) tax_data ON TRUE
                    WHERE am.state = 'posted'
                      AND am.move_type = '{journal.type_report}'
                      AND am.invoice_date >= '{journal.report_date_from}'
                      AND am.invoice_date <= '{journal.report_date_to}'
                      AND am.journal_id = {journal.id}
                    GROUP BY am.id, aa.id, am.invoice_date, am.invoice_date_due, am.sequence_number,
                             rp.bob_ref, am.payment_reference, tax_data.tax_names, rp.name
                    ORDER BY am.id ASC
                """

                cr.execute(sql)
                rows = cr.fetchall()
                columns = [desc[0] for desc in cr.description]

                # Ensure output directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Create the Excel file
                workbook = xlsxwriter.Workbook(file_path)
                worksheet = workbook.add_worksheet()

                # Write headers
                for col_num, header in enumerate(columns):
                    worksheet.write(0, col_num, header)

                # Write rows
                for row_num, row in enumerate(rows, start=1):
                    for col_num, value in enumerate(row):
                        worksheet.write(row_num, col_num, value)

                workbook.close()

                journal.url_download = f"https://diffusion-nord-sud.be/website_sale/static/description/{filename}.xlsx"
            else:
                journal.url_download = ''


class AccountMove(models.Model):
    _inherit = "account.move"

    discount_line = fields.Float(string="Remise des lignes à mettre à jour")

    def action_update_discount_lines(self):
        """Prepare the dictionary values for an invoice global discount
        line.
        """
        self.ensure_one()
        discount = self.discount_line
        for line in self.line_ids:
            line.write({'discount': discount, 'discount_primary': discount})


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _order = 'stock_move_lines asc'

    date_parution = fields.Date(compute='_compute_infos_line')
    supplier = fields.Many2one("res.partner", compute='_compute_infos_line', string="Fournisseur")
    # stock_move_lines = fields.Many2many("stock.move", compute='_compute_stock_moves', string="Lignes de livraison")
    stock_move_lines = fields.Many2many("stock.picking", compute='_compute_stock_moves', string="Lignes de livraison")
    editeur = fields.Char(string="Editeur", related="product_id.product_tmpl_id.editeur")
    discount_primary = fields.Float(string="Remise 1", default=lambda self: self.discount)
    discount_secondary = fields.Float(string="Remise 2")

    @api.model
    def create(self, vals):
        if 'discount' in vals:
            vals['discount_primary'] = vals['discount']
        return super(AccountMoveLine, self).create(vals)

    @api.onchange('discount_primary', 'discount_secondary')
    def _onchange_discount(self):
        for line in self:
            if line.discount_primary or line.discount_secondary:
                discount = 100 * ((100 - line.discount_primary) / 100) * ((100 - line.discount_secondary) / 100)
                line.discount = 100 - discount
            else:
                line.discount = line.discount_primary  # Default to primary if no secondary

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

    def _compute_stock_moves(self):
        for record in self:
            pickings = record.sale_line_ids.mapped('move_ids').filtered(lambda m: m.state == 'done').mapped(
                'picking_id')
            record.stock_move_lines = [(6, 0, pickings.ids)] if pickings else False
