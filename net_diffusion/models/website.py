# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import datetime

_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'

    def _get_slidersProduct_active(self):
        today = datetime.datetime.today()
        domain = ['|', ('date_from', '>=', today), ('date_to', '=', None)]
        domain += ['|', ('date_from', '=', None), ('date_to', '<=', today)]
        domain += [('publish', '=', True)]
        amo_sliders = self.env['website.an_slider_products'].search([])
        return amo_sliders

    def _get_slidersProduct_by_categ(self, categ):
        today = datetime.datetime.today()
        domain = ['|', ('date_from', '>=', today), ('date_to', '=', None)]
        domain += ['|', ('date_from', '=', None), ('date_to', '<=', today)]
        domain += [('publish', '=', True), ('categ_id.name', '=', categ)]
        amo_sliders = self.env['website.an_slider_products'].search(domain)
        return amo_sliders

    def get_author_tags(self, selected_ids):
        cr = self.env.cr
        sql = """SELECT id as id, name->>'fr_FR' as name FROM product_tag WHERE categ_id = 2 LIMIT 50;"""
        cr.execute(sql)
        result = cr.dictfetchall()  # Fetches list of dictionaries (id, name)

        # Sorting based on whether 'id' is in the selected_ids list
        if result:
            for item in result:
                item['selected'] = item['id'] in selected_ids  # True if in selected_ids, False otherwise

            # Optionally, you can sort the items with selected items first
            sorted_items = sorted(result, key=lambda i: i['selected'], reverse=True)
            return sorted_items

        return result  # Return as is if no result

    def get_editor_tags(self, selected_ids):
        cr = self.env.cr
        sql = """SELECT id, name->>'fr_FR' FROM product_tag WHERE categ_id = 1 LIMIT 50;"""
        cr.execute(sql)
        result = cr.dictfetchall()  # Fetches list of dictionaries (id, name)

        # Sorting based on whether 'id' is in the selected_ids list
        if result:
            for item in result:
                item['selected'] = item['id'] in selected_ids  # True if in selected_ids, False otherwise

            # Optionally, you can sort the items with selected items first
            sorted_items = sorted(result, key=lambda i: i['selected'], reverse=True)
            return sorted_items

        return result  # Return as is if no result
