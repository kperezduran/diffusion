# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Order Point Method:
#    - Order if the virtual stock of today is below the min of the defined order point
#

from odoo import models, tools

import logging
import threading

_logger = logging.getLogger(__name__)


class StockComputeUpdate(models.TransientModel):
    _name = 'sale.compute_update'
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

    def update_sale_order(self):
        cr = self.env.cr
        # Fetch data from mv_editeur with pagination
        sql = f"""
            SELECT sol.id FROM sale_order_line AS sol
             INNER JOIN sale_order AS so ON sol.order_id = so.id 
             INNER JOIN product_product AS pp ON sol.product_id = pp.id 
             INNER JOIN product_template AS pt ON pp.product_tmpl_id = pt.id 
             WHERE sol.qty_to_invoice < sol.product_uom_qty 
                    AND is_delivery IS FALSE 
                    AND sol.price_unit != pt.list_price 
                    AND so.state IN ('sale', 'draft');

        """
        cr.execute(sql)
        results = cr.dictfetchall()
        line_ids = [r['id'] for r in results]
        lines_to_update = self.env['sale.order.line'].browse(line_ids)

        for line in lines_to_update:
            if line.order_id.state == 'sale':
                line.order_id.write({
                    'locked': False
                })
                if not line.product_uom or not line.product_id:
                    line.price_unit = 0.0
                else:
                    line = line.with_company(line.company_id)
                    price = line._get_display_price()
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                        line.company_id or line.env.company,
                        line.order_id.currency_id,
                        line.order_id.date_order,
                        'sale',
                        fiscal_position=line.order_id.fiscal_position_id,
                        product_price_unit=price,
                        product_currency=line.currency_id
                    )
                line.order_id.write({
                    'locked': True
                })
            elif line.order_id.state == 'draft':
                # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
                # manually edited
                if not line.product_uom or not line.product_id:
                    line.price_unit = 0.0
                else:
                    line = line.with_company(line.company_id)
                    price = line._get_display_price()
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                        line.company_id or line.env.company,
                        line.order_id.currency_id,
                        line.order_id.date_order,
                        'sale',
                        fiscal_position=line.order_id.fiscal_position_id,
                        product_price_unit=price,
                        product_currency=line.currency_id
                    )

        return {'type': 'ir.actions.client', 'tag': 'reload'}


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
