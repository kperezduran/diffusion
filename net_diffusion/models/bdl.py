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

#
# class BDLExclu(models.Model):
#     _name = "bdl.exclu"
#     _description = "Exclusivités publication"
#
#     name = fields.Char(string="Nom")
#     nouveaute = fields.Boolean(string="Nouveauté")
#     product_ids = fields.One2many('product.template', 'exclu_id', string='Produits')


class ImportOctave(models.Model):
    _name = "import.octave"
    _description = "Import Octave"

    ean13 = fields.Char(string="EAN13", index=True)
    libelle = fields.Char(string="Libellé")
    editeur = fields.Char(string="Éditeur")
    disponibilite = fields.Char(string="Disponibilité")
    auteur = fields.Char(string="Auteur")
    fournisseur = fields.Char(string="Fournisseur")
    collection = fields.Char(string="Collection")
    numero_collection = fields.Char(string="N° Collection")
    prix_ttc = fields.Char(string="Prix TTC")
    dilicom_taux_tva = fields.Char(string="Dilicom Taux TVA")
    epaisseur = fields.Char(string="Épaisseur")
    largeur = fields.Char(string="Largeur")
    hauteur = fields.Char(string="Hauteur")
    groupe_theme = fields.Char(string="Groupe Thème")
    theme = fields.Char(string="Thème")
    poids = fields.Char(string="Poids")
    ref_fournisseur = fields.Char(string="Rèf. Fournisseur")
    fournisseur_principal = fields.Char(string="Fournisseur Principal")
    date_parution = fields.Char(string="Date Parution")
    isbn = fields.Char(string="ISBN")
    date_maj = fields.Char(string="Date MAJ")

class BDLEditor(models.Model):
    _name = 'bdl.editor'
    _description = "Éditeur Banque du livre"
    _order = "sequence asc"

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char(string="Nom", translate=True)
    active = fields.Boolean(string="Actif", default=True)
    supplier_id = fields.Many2one('bdl.supplier', string="Fournisseur BDL")
    product_line_ids = fields.One2many('bdl.editor.line', 'editor_id', string='Produits')


class BDLEditorLine(models.Model):
    _name = 'bdl.editor.line'
    _description = "Éditeur Line produit"

    editor_id = fields.Many2one('bdl.editor', string="Éditeur BDL")
    product_id = fields.Many2one('product.template', string='Produit')
    export_dilicom = fields.Boolean(string='Activer la synchronisation vers dilicom', default=False)


class BDLSupplier(models.Model):
    _name = 'bdl.supplier'
    _description = "Fournisseur Banque du livre"
    _order = "sequence asc"

    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char(string="Nom")
    gencode = fields.Char(string="gencode")
    active = fields.Boolean(string="Actif", default=True)
    product_ids = fields.One2many('product.template', 'bdl_supplier_id', string='Produits')
    editor_ids = fields.One2many('bdl.editor', 'supplier_id', string='Éditeurs')
