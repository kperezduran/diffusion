# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
import re
from pymongo import MongoClient, ASCENDING
from odoo.exceptions import ValidationError, UserError

import datetime

try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class BDLEditor(models.Model):
    _name = 'bdl.editor'
    _description = "Éditeur Bqnaue du livre"
    _order = "sequence asc"

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char(string="Nom", translate=True)
    active = fields.Boolean(string="Actif")
    product_ids = fields.One2many('product.template', 'bdl_editor_id', string='Produits')
