# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime

import datetime

try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    gencode = fields.Char(string="Gencode")
    code_octave_1 = fields.Char(string="Code Octave 1")
    code_octave_2 = fields.Char(string="Code Octave 2")
    code_octave_3 = fields.Char(string="Code Octave 3")
    code_octave_4 = fields.Char(string="Code Octave 4")
    code_octave_5 = fields.Char(string="Code Octave 5")
    be_varchar = fields.Char(string="be_varchar")
    bob_ref = fields.Char(string="Ref. Bob")