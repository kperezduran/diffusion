# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv.expression import AND, OR
import re

ISBN_MIN_LEN = 13  # seuil pour déclencher la recherche numérique

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=10):
        args = args or []
        name = (name or '').strip()
        # if not name:
        #     return super().name_search(name=name, args=args, operator=operator, limit=limit)

        # --- Cas NUMERIQUE : attendre >= 13 chiffres (on ignore séparateurs) ---
        digits = re.sub(r'\D', '', name)  # supprime tout sauf les chiffres
        if digits and digits.isdigit():
            if len(digits) < ISBN_MIN_LEN:
                # trop court, ne rien lancer
                return []
            # on force un match EXACT EAN-13 (premiers 13 chiffres au cas où >13 saisis)
            ean13 = digits[:ISBN_MIN_LEN]
            domain = [('barcode', '=', ean13)]
            ids = self._search(domain, limit=limit, order=self._order)
            return self.browse(ids).name_get()

        # --- Cas ALPHABETIQUE : exécuter seulement si il y a un espace ---
        if any(ch.isalpha() for ch in name):
            # if ' ' not in name:
            #     # on attend un 2e terme pour réduire le bruit
            #     return []

            # normaliser l'espace interne, couper, enlever tokens vides/courts
            tokens = [t for t in re.split(r'\s+', name) if t]
            tokens = [t for t in tokens if len(t) >= 2]  # optionnel: évite le bruit sur 1 lettre
            if not tokens:
                return []

            # Tous les tokens doivent matcher (AND), chaque token OR sur plusieurs champs
            per_token = []
            for tok in tokens:
                per_token.append(OR([
                    [('name', 'ilike', tok)],
                    [('default_code', 'ilike', tok)],
                ]))
            domain = AND(per_token + [args])
            ids = self._search(domain, limit=limit, order=self._order)
            return self.browse(ids).name_get()

        # --- Autres cas (mixtes, symboles, etc.) ---
        return super().name_search(name=name, args=args, operator=operator, limit=limit)