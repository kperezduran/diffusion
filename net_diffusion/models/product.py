# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

import os
import paramiko
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


host = os.getenv('SFTP_HOST', 'ftpack.centprod.com')
port = int(os.getenv('SFTP_PORT', 10022))
username = os.getenv('SFTP_USERNAME', 'DFA00071')
password = os.getenv('SFTP_PASSWORD', 'v|}Vy~2sY037')


class ProductCategory(models.Model):
    _inherit = 'product.category'

    dilicom_id = fields.Char(string="ID Dilicom")


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    dilicom_id = fields.Char(string="ID Dilicom")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    import_state = fields.Boolean(string='Créer en import', related="product_tmpl_id.import_state")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # bdl_distributeur_ids = fields.Many2many('bdl.distributeur', string='BDL Onix Distributeur')
    # bdl_editeur_ids = fields.Many2many('bdl.editeur', string='BDL Onix editeur')
    # bdl_collection_ids = fields.Many2many('bdl.collection', string='BDL Onix collection')

    dilicom_mgnt = fields.Boolean(string="Transfert Dilicom", default=False)
    is_exclu = fields.Boolean(string='Est une exclusivité', default=False)
    date_parution = fields.Date(string="Date de parution")
    dilicom_update = fields.Date(string="Date de update dilicom")
    auteur = fields.Char(string="Auteur")
    code_disponibility = fields.Char(string="code de disponibilité")
    code_impression = fields.Char(string="Impression à la demande")
    editeur = fields.Char(string="Editeur")
    collection = fields.Char(string="Collection")
    nbr_page = fields.Char(string="Nombre de pages")
    type_livre = fields.Selection(
        selection=[
            ('R', 'Relié'),
            ('B', 'Broché'),
            ('P', 'Poche'),
            ('J', 'Jeux'),
            ('D', 'Disque vinyle'),
            ('DC', 'Disque compact'),
            ('DV', 'Dique vidéo, DVD'),
            ('CD', 'CD-rom'),
            ('LD', 'Livre disque'),
            ('K', 'Cassette'),
            ('KA', 'Cassette Audio'),
            ('KV', 'Cassette vidéo'),
            ('LK', 'Livre cassette'),
            ('C', 'Cuir'),
            ('E', 'Etui'),
            ('L', 'Luxe'),
            ('X', 'Journal, revue'),
            ('SM', 'Support magnétique'),
            ('DI', 'Diapotisives'),
            ('PC', 'Publicité'),
            ('AL', 'Album'),
            ('CR', 'Cartes routières'),
            ('PO', 'Posters'),
            ('CA', 'Calendriers'),
            ('O', 'Objet'),
            ('N', 'Contenu numérique'),
        ],
        string="Type de produits",
    )
    dilicom_categ = fields.Char(string="Categorie Dilicom")
    dilicom_url = fields.Char(string="URL image Dilicom")
    dilicom_url_thumb = fields.Char(string="URL image thumbnail Dilicom")
    image_preview = fields.Html(string="Image Preview", compute="_compute_image_preview")
    import_state = fields.Boolean(string='Créer en import', default=False)
    # Computed field to separate dates before and after today
    date_sort_flag = fields.Integer(
        compute='_compute_date_sort_flag', store=True
    )
    epaisseur = fields.Integer(string="epaisseur")
    largeur = fields.Integer(string="largeur")
    hauteur = fields.Integer(string="hauteur")
    localisation = fields.Char(string="Localisation")
    bdl_supplier_id = fields.Many2one('res.partner', compute='_compute_supplier_id', store=True)

    @api.depends('seller_ids')
    def _compute_supplier_id(self):
        for record in self:
            record.bdl_supplier_id = record.seller_ids[:1].partner_id.id if record.seller_ids else None
    def _sftp_send_file(self, file_path, file_name):
        host = 'ftpack.centprod.com'
        port = 10022
        username = 'DFA00071'
        password = 'v|}Vy~2sY037'

        try:
            _logger.warning('Starting SFTP file transfer...')
            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)

            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.put(file_path, f'/I/{file_name}')
            sftp.close()
            transport.close()

            _logger.warning('CSV file successfully sent via SFTP.')
        except Exception as e:
            _logger.error(f"Failed to send CSV via SFTP: {str(e)}", exc_info=True)

    def generate_dilicom_txt(self):
        # Fetch products where dilicom_mgnt is True
        products = self.search([('dilicom_mgnt', '=', True)])
        if not products:
            raise ValidationError("No products found with 'dilicom_mgnt' set to True.")

        # Configurable file directory
        base_dir = "/opt/odoo/addons/net_diffusion/static/src/doc/dilicom"
        file_name = 'MAJ - ' + fields.Datetime.now().strftime('%Y%m%d%H%M%S') + ".txt"
        file_dir = os.getenv('DILICOM_DIR', base_dir)  # Use env variable if available
        file_path = os.path.join(file_dir, file_name)  # Full path to the file

        # Ensure the directory exists and is writable
        try:
            os.makedirs(file_dir, exist_ok=True)
            if not os.access(file_dir, os.W_OK):
                raise ValidationError(f"Directory '{file_dir}' is not writable.")
        except Exception as e:
            raise ValidationError(f"Failed to prepare directory '{file_dir}': {e}")

        # Helper function to pad or truncate a field
        def fixed_width(value, length):
            value = str(value or "").strip().replace("\n", " ").replace("\r", " ")
            return value[:length].ljust(length)
        # Helper function to pad or truncate a field

        def fixed_widthr(value, length):
            value = str(value or "").strip().replace("\n", " ").replace("\r", " ")
            return value[:length].rjust(length)

        # Open the file for writing
        try:
            with open(file_path, "w", encoding="utf-8") as txt_file:
                for product in products:
                    row = (
                            fixed_width("M", 1) +  # movement_code
                            fixed_width(product.barcode, 13) +  # isbn_13
                            fixed_width("3012405014701", 13) +  # gencode
                            fixed_width(fields.Datetime.now().strftime('%Y%m%D'), 8) +  # application_date
                            fixed_width(product.code_disponibility, 1) +  # code_disponibility
                            fixed_width(4, 1) +  # price_type
                            fixed_width(str(int(product.list_price * 1000)).zfill(8), 8) +  # price_ttc
                            fixed_width("", 2) +  # remise_type
                            fixed_width(str(int(product.taxes_id[0].amount * 100)).zfill(4), 4) +  # tva1
                            fixed_width(str(int((product.list_price / ((100 + product.taxes_id[0].amount)/100))*100)*10).replace(',','').zfill(8), 8) +  # htva1
                            fixed_width("", 4) +  # tva2
                            fixed_width("", 8) +  # htva2
                            fixed_width("", 4) +  # tva3
                            fixed_width("", 8) +  # htva3
                            fixed_width("1", 1) +  # code_retour
                            "1         " +  # code_prix
                            fixed_width(product.date_parution.strftime('%Y%m%D'), 8) +  # date_parution
                            "01" +
                            fixed_width("", 8) +  # date_endsale
                            fixed_widthr(product.name, 30) +  # name
                            fixed_widthr(product.name, 20) +  # name_pos
                            fixed_widthr("", 2) +  # presentation_shop
                            fixed_width(product.epaisseur, 4) +  # epaisseur
                            fixed_width(product.largeur, 4) +  # largeur
                            fixed_width(product.hauteur, 4) +  # hauteur
                            fixed_width(product.weight, 7) +  # poids
                            fixed_width(product.name, 100) +  # name_long
                            fixed_width(product.editeur, 15) +  # editor
                            fixed_width(product.collection, 15) +  # collection
                            fixed_width(product.auteur, 20) +  # author
                            fixed_width(product.type_livre, 2) +  # presentation_shop
                            fixed_width(product.barcode[3:], 10) +  # isbn
                            fixed_width("", 12) +  # supplier_ref
                            fixed_width("", 10) +  # collection_serie
                            fixed_width(product.dilicom_categ, 4) +  # theme
                            fixed_width("", 8) +  # isbn_editor
                            fixed_width("", 1) +  # code_link
                            fixed_width("", 13) +  # linked_product_ean
                            "1" +  # article_per_unit
                            "0" +  # vente_colis
                            "1" +  # symbolisation
                            "1" +  # product_perrisable
                            fixed_width("", 4) +  # nbr_ref
                            "\n"
                    )
                    if len(row) != 402:
                        raise ValidationError(
                            f"Generated row length {len(row)} does not meet the 402-character requirement.")
                    txt_file.write(row)
        except Exception as e:
            raise ValidationError(f"Failed to write to file '{file_path}': {e}")

        # return True
        self._sftp_send_file(file_path, file_name)

    @api.depends('date_parution')
    def _compute_date_sort_flag(self):
        today = fields.Date.today()
        for record in self:
            if record.date_parution:
                if record.date_parution >= today:
                    record.date_sort_flag = 1
                else:
                    record.date_sort_flag = 0
            else:
                record.date_sort_flag = 0

    def _compute_image_preview(self):
        for record in self:
            if record.dilicom_url:
                # Générer un tag HTML pour afficher l'image
                record.image_preview = f'<img src="{record.dilicom_url}" style="max-width:200px; max-height:200px;" alt="Image preview"/>'
            else:
                record.image_preview = ''

    def update_mongo(self):
        # MongoDB connection
        cr = self.env.cr
        client = MongoClient("mongodb://172.30.0.47:27017/")
        db = client.book_store  # Use your MongoDB database name
        collection = db.dilicom_books

        # Get all product barcodes
        product_records = self.env['product.template'].search([('barcode', '!=', None)])
        barcodes = [product.barcode for product in product_records]

        # Fetch books from MongoDB that match the barcodes in PostgreSQL
        books_data = collection.find({"isbn_13": {"$in": barcodes}})
        # Loop through the MongoDB results
        for book in books_data:
            if 'author' in book:  # Ensure 'author' field exists in the MongoDB document
                # Update PostgreSQL records using a parameterized query to avoid SQL injection
                cr.execute("""
                    UPDATE product_template
                    SET auteur = %s
                    WHERE id = (
                        SELECT pt.id 
                        FROM product_product AS pp 
                        JOIN product_template AS pt ON pp.product_tmpl_id = pt.id 
                        WHERE pp.barcode = %s
                    )
                """, (book['author'], book['isbn_13']))

        # Commit the changes to the database
        self.env.cr.commit()

    def get_windev_product(self, barcode=None):
        # if not barcode:
        #     barcode = '9780123456789'
        self.ensure_one()
        if barcode:
            try:
                # Execute the query
                self.env.cr.execute('''
                    SELECT emp.name, pp.barcode, pt.dilicom_url, pt.name->>'fr_FR', pt.collection, pt.editeur, pt.auteur, sq.quantity, pt.list_price, pt.localisation
                    FROM product_template AS pt
                    INNER JOIN product_product AS pp ON pp.product_tmpl_id = pt.id
                    LEFT JOIN stock_putaway_rule AS spr ON spr.product_id = pp.id
                    LEFT JOIN stock_location AS emp ON emp.id = spr.location_out_id
                    LEFT JOIN stock_quant AS sq ON sq.product_id = pp.id
                    WHERE  pp.barcode = %s;
                ''', (barcode,))

                # Fetch results
                results = self.env.cr.fetchall()

                # Replace None with empty strings
                data = [
                    {
                        'emplacement': row[0] or '',
                        'barcode': row[1] or '',
                        'image': row[2] or '',
                        'name': row[3] or '',
                        'collection': row[4] or '',
                        'editeur': row[5] or '',
                        'auteur': row[6] or '',
                        'quantite': row[7] or 0,
                        'prix': row[8] or 0,
                        'localisation': row[9] or '',
                    }
                    for row in results
                ]

                return {'status': 'success', 'data': data or []}

            except Exception as e:
                return {'status': 'error', 'message': str(e)}
        else:
            return {'status': 'error', 'message': 'Barcode is required'}

    def change_product_localisation(self, barcode=None, localisation=None):
        self.ensure_one()
        try:
            if not barcode and not localisation:
                return {'status': 'error', 'message': 'barcode and localisation is required'}
            else:
                self.env.cr.execute('''
                        UPDATE product_template set localisation=%s where id = (select product_tmpl_id from product_product where barcode = %s);''', (localisation, barcode,))
                return {'status': 'success', 'message': 'product localisation updated'}
        except Exception as e:
            return {'status': 'error', 'message': 'grosse erreur'}
        
    
    def get_windev_location(self):
        # if not barcode:
        #     barcode = '9780123456789'
        self.ensure_one()
        try:
            # Execute the query
            self.env.cr.execute('''
                SELECT emp.id, emp.name
FROM stock_location AS emp where id = 8 or (id > 7097 and usage = 'internal') order by id asc;
            ''')

            # Fetch results
            results = self.env.cr.fetchall()

            # Replace None with empty strings
            data = [
                {
                    'id': row[0] or '',
                    'name': row[1] or '',
                }
                for row in results
            ]

            return {'status': 'success', 'data': data or []}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_windev_assign_strategy(self, barcode=None, location_id=None):
        # if not barcode:
        #     barcode = '9780123456789'
        self.ensure_one()
        if barcode and location_id:
            try:
                # Execute the query
                product = self.env['product.product'].search([('barcode', '=', barcode)])
                location = self.env['stock.location'].browse(int(location_id))
                strategy = self.env['stock.putaway.rule'].search([('product_id', '=', product.id)], limit=1)
                if strategy:
                    if strategy.location_out_id != location.id:
                        strategy.write({
                            'location_out_id': location.id,
                        })

                else:
                    strategy = self.env['stock.putaway.rule'].create({
                        'product_id': product.id,
                        'location_out_id': location.id,
                        'location_in_id': 8,
                    })

                return {'status': 'success', 'data': strategy.id or []}

            except Exception as e:
                return {'status': 'error', 'message': str(e)}
        else:
            return {'status': 'error', 'message': 'Barcode is required'}

    def get_windev_product_stock(self, barcode=None):
        # if not barcode:
        #     barcode = '9780123456789'
        self.ensure_one()
        if barcode:
            try:
                # Execute the query
                self.env.cr.execute('''
                    SELECT emp.name, emp.id, pp.barcode, pt.dilicom_url, pt.name->>'fr_FR',
                     pt.collection, pt.editeur, pt.auteur, emp2.name, emp2.id, sq.quantity,
                      string_agg(rp.name, ';') AS supplier_name, pt.localisation, pt.code_disponibility
                    FROM product_template AS pt
                    INNER JOIN product_product AS pp ON pp.product_tmpl_id = pt.id
                    LEFT JOIN stock_putaway_rule AS spr ON spr.product_id = pp.id
                    LEFT JOIN stock_location AS emp ON emp.id = spr.location_out_id
                    LEFT JOIN stock_quant AS sq ON sq.product_id = pp.id
                    LEFT JOIN stock_location AS emp2 ON emp2.id = sq.location_id
                    LEFT JOIN product_supplierinfo AS psi ON psi.product_tmpl_id = pt.id
                    LEFT JOIN res_partner AS rp ON rp.id = psi.partner_id
                    WHERE emp2.usage = 'internal' AND pp.barcode = %s GROUP BY emp.name, emp.id, pp.barcode, pt.dilicom_url, pt.name->>'fr_FR', pt.collection, pt.editeur, pt.auteur, emp2.name, emp2.id, sq.quantity, pt.localisation, pt.code_disponibility;
                ''', (barcode,))

                # Fetch results
                results = self.env.cr.fetchall()

                # Replace None with empty strings
                data = [
                    {
                        'emplacement': row[0] or '',
                        'emplacement_id': row[1] or '',
                        'barcode': row[2] or '',
                        'image': row[3] or '',
                        'name': row[4] or '',
                        'collection': row[5] or '',
                        'editeur': row[6] or '',
                        'auteur': row[7] or '',
                        'stock': row[8] or '',
                        'stock_id': row[9] or '',
                        'quantite': row[10] or 0,
                        'fournisseur': row[11] or 0,
                        'localisation': row[12] or '',
                        'dispo': row[13] or '',
                    }
                    for row in results
                ]

                return {'status': 'success', 'data': data or []}

            except Exception as e:
                return {'status': 'error', 'message': str(e)}
        else:
            return {'status': 'error', 'message': 'Barcode is required'}

    def get_windev_picking_products(self, picking=None):
        # if not barcode:
        #     barcode = '9780123456789'
        self.ensure_one()
        if picking:
            try:
                # Execute the query
                self.env.cr.execute('''
                    select pp.barcode, sm.quantity  from stock_picking as sp
                        inner join stock_move as sm on sm.picking_id = sp.id
                        inner join product_product as pp on sm.product_id = pp.id
                        inner join product_template as pt on pp.product_tmpl_id = pt.id
                    where sp.state in ('assigned', 'confirmed') and sp.picking_type_id = 2 and sp.name =%s and sm.quantity > 0;
                                    ''', (picking,))

                # Fetch results
                results = self.env.cr.fetchall()

                # Replace None with empty strings
                data = [
                    {
                        'ean': row[0] or '',
                        'quantite': row[1] or '',
                    }
                    for row in results
                ]

                return {'status': 'success', 'data': data or []}

            except Exception as e:
                return {'status': 'error', 'message': str(e)}
        else:
            return {'status': 'error', 'message': 'Barcode is required'}

    def get_windev_get_po_client(self, purchase=None):
        # if not barcode:
        #     barcode = '9780123456789'
        self.ensure_one()
        if purchase:
            try:
                # Execute the query
                self.env.cr.execute('''
                    select so.name, rp.name  from purchase_order as po
                        inner join sale_order as so on so.id = po.sale_order_id
                        inner join res_partner as rp on rp.id = so.parnter_id                        
                    where po.is_dedie is true and po.name = %s;''', (purchase,))

                # Fetch results
                results = self.env.cr.fetchall()

                # Replace None with empty strings
                data = [
                    {
                        'command': row[0] or '',
                        'client': row[1] or '',
                    }
                    for row in results
                ]

                return {'status': 'success', 'data': data or []}

            except Exception as e:
                return {'status': 'error', 'message': str(e)}
        else:
            return {'status': 'error', 'message': 'Barcode is required'}

    def get_windev_product_sale_order(self, barcode=None):
        # if not barcode:
        #     barcode = '9780123456789'
        self.ensure_one()
        if barcode:
            try:
                # Execute the query
                self.env.cr.execute('''
                    select so.id, so.name, rp.id, rp.name, rp.email, pp.barcode, pp.id,  sol.product_uom_qty - sol.qty_delivered 
                        from sale_order as so 
                            inner join sale_order_line as sol on so.id = sol.order_id
                            inner join product_product as pp on sol.product_id = pp.id
                            inner join res_partner as rp on so.partner_id = rp.id
                        where sol.product_uom_qty != sol.qty_delivered and pp.barcode = %s and so.state = 'sale';
                ''', (barcode,))

                # Fetch results
                results = self.env.cr.fetchall()

                # Replace None with empty strings
                data = [
                    {
                        'sale_order_id': row[0] or '',
                        'sale_order': row[1] or '',
                        'partner_id': row[2] or '',
                        'partner_name': row[3] or '',
                        'partner_mail': row[4] or '',
                        'barcode': row[5] or '',
                        'product_id': row[6] or '',
                        'quantity_restant': row[7] or '',
                    }
                    for row in results
                ]

                return {'status': 'success', 'data': data or []}

            except Exception as e:
                return {'status': 'error', 'message': str(e)}
        else:
            return {'status': 'error', 'message': 'Barcode is required'}

    def get_windev_stock_move(self, barcode=None, location_origin=None, location_dest=None, quantity=None):
        if not barcode or not location_origin or not location_dest or not quantity:
            return {'status': 'error', 'message': 'Barcode, locations, and quantity are required.'}

        try:
            # Get product
            product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
            if not product:
                return {'status': 'error', 'message': 'Product not found for the given barcode.'}

            # Get locations
            location_o = self.env['stock.location'].browse(int(location_origin))
            location_d = self.env['stock.location'].browse(int(location_dest))
            if not location_o.exists() or not location_d.exists():
                return {'status': 'error', 'message': 'Invalid origin or destination location.'}

            # Get picking type
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)
            if not picking_type:
                return {'status': 'error', 'message': 'Internal picking type not found.'}

            # Create picking
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': location_o.id,
                'location_dest_id': location_d.id,
                'origin': f'Transfer {product.name}',
            })

            # Create stock move
            move = self.env['stock.move'].create({
                'name': f'Transfer {product.name}',
                'product_id': product.id,
                'product_uom_qty': quantity,
                'product_uom': product.uom_id.id,
                'location_id': location_o.id,
                'location_dest_id': location_d.id,
                'picking_id': picking.id,
            })

            # Confirm the move
            move._action_confirm()

            # Check stock availability
            stock_quant = self.env['stock.quant'].search(
                [('product_id', '=', product.id), ('location_id', '=', location_o.id)]
            )
            available_quantity = sum(stock_quant.mapped('quantity')) - sum(stock_quant.mapped('reserved_quantity'))
            reserved_moves = False
            if available_quantity < quantity:
                # Check and reallocate reserved stock from other pickings
                reserved_moves = self.env['stock.move.line'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', location_o.id),
                    ('state', 'not in', ['done', 'cancel'])
                ])

                # Free up reserved quantities from other pickings
                freed_quantity = 0
                for reserved_move in reserved_moves:
                    if freed_quantity >= (quantity - available_quantity):
                        break

                    # Calculate how much can be released
                    release_quantity = min(reserved_move.quantity, quantity - available_quantity - freed_quantity)
                    if release_quantity > 0:
                        reserved_move.quantity -= release_quantity
                        reserved_move.move_id._recompute_state()
                        freed_quantity += release_quantity

                # Recheck availability after releasing stock
                stock_quant = self.env['stock.quant'].search(
                    [('product_id', '=', product.id), ('location_id', '=', location_o.id)]
                )
                available_quantity = sum(stock_quant.mapped('quantity')) - sum(stock_quant.mapped('reserved_quantity'))

                if available_quantity < quantity:
                    return {'status': 'error',
                            'message': 'Insufficient stock in the source location even after reallocation.'}

            # Create move lines and set quantities
            move_line = self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'qty_done': quantity,
                'location_id': location_o.id,
                'location_dest_id': location_d.id,
            })

            # Reserve quantities and validate the picking
            picking.action_assign()  # Reserve quantities
            picking.with_context(skip_stock_quant_check=True).button_validate()

            for reserved_move in reserved_moves:
                reserved_move.move_id.picking_id.action_assign()
            return {'status': 'success', 'message': 'Stock move completed successfully', 'picking_state': picking.state}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_product_mongo(self):
        cr = self.env.cr
        client = MongoClient("mongodb://172.30.0.47:27017/")
        db = client.book_store  # Use your MongoDB database name
        collection = db.dilicom_books
        collection_processed = db.dilicom_books_processed

        # Fetch supplier references from PostgreSQL
        cr.execute("""SELECT gencode FROM res_partner WHERE gencode IS NOT NULL;""")
        suppliers_ref = cr.dictfetchall()

        # Extract 'ref' values from suppliers_ref into a list
        supplier_refs_list = [supplier['gencode'] for supplier in suppliers_ref]

        # MongoDB query
        books_data = collection.find(
            {
                "processed": False,
                "gencode": {"$in": supplier_refs_list},  # Use the extracted supplier refs
                "movement_code": {"$ne": "S"}  # Exclude movement_code equal to 'S'
            },
            {
                "isbn_13": 1,  # Project only isbn_13
                "name": 1,  # Project only name
                "_id": 0  # Exclude _id
            }
        )

        for book in books_data:

            # Safely retrieve the 'isbn_13' and 'name' fields from the MongoDB document
            ean_13 = book['isbn_13']
            label = book.get('name')  # Fallback to 'Unknown' if name is not found

            # Search for existing product by barcode
            product = self.env['product.template'].search([('barcode', '=', ean_13)], limit=1)

            # If no product exists, create a new one
            if not product and ean_13:
                # Create the new product in Odoo
                self.env['product.template'].create({
                    'name': label if label else 'Unkown',  # Use 'label' from MongoDB, fallback to 'Unknown'
                    'barcode': ean_13,
                    'type': 'product',
                    'sale_ok': True,
                    'purchase_ok': True,
                    'is_published': True,
                })
            book_processed = {'isbn_13': ean_13}
            collection.update_one(
                {'isbn_13': ean_13},  # Find document where 'isbn_13' matches ean_13
                {'$set': {'processed': True}}  # Update the 'processed' field to true
            )

            books_already = collection_processed.find(
                {
                    'isbn_13': ean_13
                }
            )
            if not books_already:
                collection_processed.insert_one(book_processed)

            book_cursor = collection.aggregate([
                {
                    "$match": {
                        "isbn_13": ean_13,
                        "gencode": {"$in": supplier_refs_list}  # Use the extracted supplier refs
                    }
                },
                {
                    "$group": {
                        "_id": "$isbn_13",  # Group by the isbn_13 field
                        "isbn_13": {"$first": "$isbn_13"},  # Keep the first isbn_13
                        "name_long": {"$first": "$name_long"},  # Take the first occurrence of name_long
                        "editor": {"$first": "$editor"},  # Take the first occurrence of editor
                        "author": {"$first": "$author"},  # Take the first occurrence of author
                        "date_parution": {"$first": "$date_parution"},  # Take the first date_parution
                        "price_ttc": {"$first": "$price_ttc"},  # Take the first htva1
                        "theme": {"$first": "$theme"},  # Take the first occurrence of theme
                        "url_full": {"$first": "$url_full"},  # Take the first occurrence of theme
                        "gencode": {"$first": "$gencode"},  # Take the first occurrence of theme
                        "url_thumbnail": {"$first": "$url_thumbnail"},  # Take the first occurrence of theme
                        "code_disponibility": {"$first": "$code_disponibility"},
                        "code_prix": {"$first": "$code_prix"},
                        "collection": {"$first": "$collection"},
                        "editor_presentation": {"$first": "$editor_presentation"}
                    }
                }
            ])
            book_list = list(book_cursor)
            if book_list:  # Check if the list is not empty
                book = book_list[0]
            else:
                book = None

            if book:
                name_long = book['name_long']
                if not name_long:
                    name_long = ""  # Fallback if no value is present
                htva1 = False
                if book.get('price_ttc'):
                    htva1 = int(book['price_ttc']) / 1000
                if not htva1:
                    htva1 = 0
                cr.execute("""
                                UPDATE product_template 
                                SET list_price = CAST(%s as FLOAT), 
                                    auteur = %s, 
                                    editeur = %s, 
                                    date_parution = CASE WHEN %s IS NOT NULL THEN TO_DATE(%s, 'YYYYMMDD') ELSE NULL END,
                                    dilicom_categ = %s, 
                                    name = jsonb_set(name, '{fr_FR}', to_jsonb(CAST(%s as TEXT)), true),
                                    dilicom_url = %s, 
                                    dilicom_url_thumb = %s,
                                    code_disponibility = %s,
                                    code_impression = %s,
                                    collection = %s,
                                    type_livre = %s,
                                    write_date = now()
                                WHERE id IN (
                                    SELECT pp2.product_tmpl_id 
                                    FROM product_product AS pp2 
                                    WHERE pp2.barcode = %s
                                );
                            """, (
                    htva1, book['author'], book['editor'], book['date_parution'], book['date_parution'], book['theme'],
                    name_long, book['url_full'], book['url_thumbnail'], book['code_disponibility'],
                    book['code_prix'], book['collection'], book['editor_presentation'], book['isbn_13']))
                # Commit the changes if necessary (optional depending on your environment)
                # cr.execute("""
                #     insert into product_supplierinfo
                #     (
                #     partner_id, sequence, company_id, currency_id, product_tmpl_id, delay, create_uid, write_uid, min_qty,
                #     price, create_date, write_date
                #     )
                #     (
                #      select rp.id, 1, 1, 125, pt.id, 1, 1, 1, 1,
                #      pt.list_price, now(), now()
                #      from product_template as pt
                #      inner join product_product as pp on pt.id = pp.product_tmpl_id
                #      inner join res_partner as rp on rp.ref= %s where pp.barcode = %s
                #      left join product_supplierinfo as psi on rp.id = psi.partner_id and pt.id = psi.product_tmpl_id
                #      where psi.partner_id is null
                #     );
                # """, (book['gencode'], ean_13, book['gencode'], ean_13))

        cr.commit()
