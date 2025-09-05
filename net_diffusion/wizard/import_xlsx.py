# -*- coding: utf-8 -*-
import logging
import ezodf
import tempfile
import requests
import re
from struct import pack

_logger = logging.getLogger(__name__)
import io
from io import BytesIO
from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P
import base64
import csv
from odoo import models, fields, _
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import openpyxl
from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P
import pandas as pd
from Crypto.Cipher import Blowfish

try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')

try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')

try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')
# API Keys and base URLs for each API
ISBNDB_API_KEY = "55896_0d3b8dcd79ce08dd77404d165fffed49"
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_API_URL = "https://openlibrary.org/api/books"


class WizardImportOctave(models.TransientModel):
    _name = "wizard.import_octave"

    file = fields.Binary(string='Fichier')
    editor_id = fields.Many2many('bdl.editor', string="Éditeur BDL")
    supplier_id = fields.Many2one('res.partner', string="Fournisseur")

    def parse_date(self, date_str):
        try:
            # Try the first format (day/month/year)
            return datetime.strptime(date_str, '%d/%m/%Y')
        except ValueError:
            # If the first format fails, try the second format (year-month-day)
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                # If both formats fail, return None or handle as needed
                print(f"Date format not recognized for {date_str}")
                return None

    def make_import(self):
        """
        Import CSV file into import.octave model, filtering for Editeur = GALLIMARD.
        Includes line-by-line reading for large or malformed CSV files.
        """
        if not self.file:
            raise models.ValidationError("Please upload a valid CSV file.")
        cr = self.env.cr
        Product = self.env['product.template']
        Dispo = self.env['dr.product.label']
        cr.execute("""DELETE FROM import_octave;""")
        cr.commit()
        # Decode the uploaded file
        try:
            # Attempt UTF-8 decoding
            file_data = base64.b64decode(self.file).decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Fallback to ISO-8859-1 (common for Excel CSVs)
                file_data = base64.b64decode(self.file).decode('iso-8859-1')
            except UnicodeDecodeError as e:
                # Raise an error if decoding fails
                raise models.ValidationError("The uploaded file has unsupported encoding: %s" % str(e))

        # Detect delimiter
        try:
            # Attempt to infer the delimiter dynamically
            dialect = csv.Sniffer().sniff(file_data.splitlines()[0])
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ','  # Fallback to default

        # Process file line by line to avoid buffer overflow
        records = []
        skipped_rows = []
        reader = csv.DictReader(io.StringIO(file_data), delimiter=delimiter)

        # Map CSV columns to model fields
        field_mapping = {
            'EAN13': 'ean13',
            'Libelle': 'libelle',
            'Editeur': 'editeur',
            'Disponibilite': 'disponibilite',
            'Auteur': 'auteur',
            'Fournisseur': 'fournisseur',
            'Collection': 'collection',
            'N° Collection': 'numero_collection',
            'Prix TTC': 'prix_ttc',
            'DilicomTauxTVA': 'dilicom_taux_tva',
            'Epaisseur': 'epaisseur',
            'Largeur': 'largeur',
            'Hauteur': 'hauteur',
            'Groupe Thème': 'groupe_theme',
            'Thème': 'theme',
            'Poids': 'poids',
            'Rèf. Fournisseur': 'ref_fournisseur',
            'FournisseurPrincipal': 'fournisseur_principal',
            'Date Parution': 'date_parution',
            'ISBN': 'isbn',
            'DateMAJ': 'date_maj',
        }
        iterator = 0
        for line_number, row in enumerate(reader, start=1):
            try:
                iterator += 1
                # Only process rows where 'Editeur' equals 'GALLIMARD'
                if row.get('Editeur', ''):
                    if self.editor_id:
                        if row.get('Editeur', '').strip().lower() in map(str.lower, self.editor_id.mapped('name')):
                            record_data = {field_mapping[col]: row[col] for col in field_mapping if col in row}
                            record_data['id'] = iterator
                            records.append(record_data)
                    else:
                        # Map and prepare record
                        record_data = {field_mapping[col]: row[col] for col in field_mapping if col in row}
                        record_data['id'] = iterator
                        records.append(record_data)
            except Exception as e:
                # Log problematic rows
                skipped_rows.append((line_number, str(e)))

        # Insert valid records
        if records:
            self.env['import.octave'].create(records)

        cr.execute("""select io.* from import_octave as io left join product_product as pp on io.ean13 = pp.barcode where pp.barcode is null;""")
        cr.commit()
        results = cr.fetchall()
        products_data = []
        supplierinfo_data = []

        disponibility_mapping = {
            'Arret Commercial': '6',
            'Changement Distribut': '5',
            'Disponible': '1',
            'Fiche Provisoire': '2',
            'Manquant Sans Date': '7',
            'Non Dispo Provisoire': '4',
            'Pas Paru': '2',
            'Réimpr. en Cours': '3',
        }

        for disponibility, code in disponibility_mapping.items():
            cr.execute(
                """
                SELECT io.ean13
                FROM import_octave AS io
                LEFT JOIN product_product AS pp ON io.ean13 = pp.barcode
                WHERE pp.barcode IS NOT NULL AND disponibilite = %s;
                """,
                (disponibility,)  # Pass as a single-item tuple
            )
            results_ean = cr.fetchall()
            barcodes = [result[0] for result in results_ean]
            _logger.info(barcodes[0:10])
            update_products = self.env['product.template'].search([('barcode', 'in', barcodes)])
            dr_label_id = Dispo.search([('x_dilicom_code', 'ilike', code)])

            update_products.write({
                'is_published': True,
                'dr_label_id': dr_label_id.id if dr_label_id else False
            })

        for result in results:
            cr.execute("""
                SELECT pc.id 
                FROM product_category pc 
                WHERE lower(pc.name) LIKE lower(%s || '%%');
            """, (result[17],))
            categ_result = cr.fetchall()

            # _logger.info(f'{result[3]}.')
            bs = Blowfish.block_size
            key = b'WGt5cMq8M6cN3q6j'
            iv = b'00000000'  # Must be 8 bytes for Blowfish CBC mode

            # Blowfish cipher setup
            cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv=iv)

            # Image URLs and data
            clt_gln_13 = '3025594674304'
            url_img = 'https://images.centprod.com/' + clt_gln_13
            gln_13 = self.supplier_id.ref
            ean_13 = result[3]
            # String to encrypt
            string_toEncrypt = 'DILICOM:' + str(ean_13) + '-' + str(gln_13)
            string_toEncrypt = bytes(string_toEncrypt, 'utf-8')

            # Padding the string to match block size
            plen = bs - (len(string_toEncrypt) % bs)
            padding = [plen] * plen
            padding = pack('b' * plen, *padding)

            # Encrypting the message
            msg = cipher.encrypt(string_toEncrypt + padding)

            # Encoding the message to URL-safe base64
            msg = base64.urlsafe_b64encode(msg)

            # Creating the final image URL
            url = url_img + '/' + str(msg, 'utf-8') + '-cover-full.jpg'
            url_thumb = url_img + '/' + str(msg, 'utf-8') + '-cover-thumb.jpg'

            # new_product = Product.create({
            #     'barcode': result[3],
            #     'name': result[4],
            #     'editeur': result[5],
            #     'auteur': result[7],
            #     'collection': result[10],
            #     'dr_label_id': disponibility_mapping.get(result[6]) if disponibility_mapping.get(result[6]) else None,
            #     'type': 'product',
            #     'dilicom_url': url,
            #     'dilicom_url_thumb': url_thumb,
            #     'list_price': result[11].replace(',','.'),
            #     'date_parution': fields.datetime.strptime(result[21], '%d/%m/%Y'),
            #     'categ_id': categ_result[0][0] if categ_result else 1,
            # })
            # self.env['product.supplierinfo'].create({
            #     'partner_id': self.supplier_id.id,
            #     'product_tmpl_id': new_product.id,
            #     'price': new_product.list_price,
            # })
            list_price = result[11].replace(',', '.')
            date_parution = self.parse_date(result[21])
            categ_id = categ_result[0][0] if categ_result else 1
            dr_label_id = Dispo.search([('x_dilicom_code', 'ilike', disponibility_mapping.get(result[6]))]) if disponibility_mapping.get(result[6]) else None

            # Prepare product data
            product_data = {
                'barcode': result[3],
                'default_code': result[3],
                'name': result[4],
                'editeur': result[5],
                'auteur': result[7],
                'collection': result[10],
                'dr_label_id': dr_label_id.id if dr_label_id else False,
                'type': 'product',
                'dilicom_url': url,
                'dilicom_url_thumb': url_thumb,
                'list_price': list_price,
                'date_parution': date_parution,
                'categ_id': categ_id,
                'is_published': True,
            }
            products_data.append(product_data)

            # Batch create products
        created_products = self.env['product.template'].create(products_data)

        # Prepare supplier info data
        for product, result in zip(created_products, results):
            supplierinfo_data.append({
                'partner_id': self.supplier_id.id,
                'product_tmpl_id': product.id,
                'price': product.list_price,
            })

            # Batch create supplier info
        self.env['product.supplierinfo'].create(supplierinfo_data)
        # Report skipped rows
        if skipped_rows:
            skipped_message = "\n".join([f"Line {ln}: {error}" for ln, error in skipped_rows])
            raise models.ValidationError("Some rows were skipped due to errors:\n%s" % skipped_message)

        if not records:
            raise models.ValidationError(_("No valid records found in the file."))

        cr.execute("""DELETE FROM import_octave;""")
        cr.commit()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class ImportXLSXInvoice(models.TransientModel):
    _name = "wizard.import_xlsx_order"

    file_xls = fields.Binary(string='Fichier Excel')
    file_ods = fields.Binary(string='Fichier ODS')
    sale_order_id = fields.Many2one('sale.order', string='Commande')

    # Function to fetch data from ISBNdb, including the price if available
    def fetch_from_isbndb(self, isbn):
        # Headers for ISBNdb API
        isbn_db_headers = {
            "accept": "application/json",
            "Authorization": ISBNDB_API_KEY,
        }

        url = f"https://api2.isbndb.com/book/{isbn}"
        response = requests.get(url, headers=isbn_db_headers)

        if response.status_code == 200:
            data = response.json()
            # Attempt to fetch price from the response
            return {"data": data}
        return None

    # Function to fetch data from Google Books, including the price if available
    def fetch_from_google_books(self, isbn):
        params = {"q": f"isbn:{isbn}"}
        response = requests.get(GOOGLE_BOOKS_API_URL, params=params)
        data = response.json()
        if "items" in data:
            book_data = data["items"][0]
            # Attempt to fetch price from the saleInfo section
            sale_info = book_data.get("saleInfo", {})
            price = sale_info.get("listPrice", {}).get("amount")
            currency = sale_info.get("listPrice", {}).get("currencyCode")
            return {"data": book_data, "price": price, "currency": currency}
        return None

    # Function to fetch data from Open Library
    def fetch_from_open_library(self, isbn):
        url = f"{OPEN_LIBRARY_API_URL}?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        response = requests.get(url)
        data = response.json().get(f"ISBN:{isbn}")

        # Open Library typically does not provide price information
        return {"data": data, "price": None}

    def get_cell_value(self, cell):
        """Extract the text content from a cell."""
        paragraphs = cell.getElementsByType(P)
        cell_value = ''.join(
            paragraph.firstChild.data if paragraph.firstChild else '' for paragraph in paragraphs).strip()
        return cell_value

    def make_invoice_line(self):
        for wizard in self:
            product_model = self.env['product.product']
            product_template = self.env['product.template']
            order_line_model = self.env['sale.order.line']
            order = wizard.sale_order_id
            pattern = r'^\d{13}$'
            if wizard.file_xls:
                if not wizard.file_xls:
                    raise UserError(_("Please upload an Excel file to proceed."))
                if not wizard.sale_order_id:
                    raise UserError(_("Please select a sale order to update."))

                # Decode the uploaded XLSX file from base64
                try:
                    file_content = base64.b64decode(wizard.file_xls)
                    # Use BytesIO to load the file into openpyxl
                    excel_file = io.BytesIO(file_content)
                    workbook = openpyxl.load_workbook(excel_file, data_only=True)
                    sheet = workbook.active  # You can select a specific sheet if necessary
                except Exception as e:
                    raise UserError(_("Error while reading the Excel file: %s") % e)

                # Prepare the sale.order.line model for creating order lines
                iterator = 0
                # Iterate through rows in the sheet, assuming the barcode is in column A (index 1)
                last_line = order_line_model.search([('order_id', '=', order.id), ('is_delivery', '=', False)],
                                                    limit=1, order="sequence desc")
                if last_line:
                    iterator = last_line.sequence
                    # raise ValidationError(iterator)
                for row in sheet.iter_rows(min_row=2, values_only=True):  # Skips header row
                    barcode = row[0]  # Assuming column A contains the barcode
                    iterator += 1
                    if not barcode:
                        continue  # Skip empty rows

                    # Search for product by barcode
                    product = product_model.search([('barcode', '=', barcode)], limit=1)

                    # Check if the input string consists of exactly 13 digits

                    if not product and re.match(pattern, barcode):
                        isbn_db_data = self.fetch_from_isbndb(barcode)
                        # google_books_data = self.fetch_from_google_books(barcode)
                        # open_library_data = self.fetch_from_open_library(barcode)
                        product_template = product_template.create({
                            'barcode': barcode,
                            'name': isbn_db_data['data'].get('book').get('title_long'),
                            'dilicom_url': isbn_db_data['data'].get('book').get('image'),
                            'dilicom_url_thumb': isbn_db_data['data'].get('book').get('image'),
                            'editeur': isbn_db_data['data'].get('book').get('publisher'),
                            'auteur': isbn_db_data['data'].get('book').get('authors'),
                            'description_ecommerce': isbn_db_data['data'].get('book').get('synopsis'),
                            'default_code': barcode,
                            'type': 'product',
                            'import_state': True,
                        })
                        product = product_template.product_variant_id

                    if product:
                        quantity = 1
                        if len(row) > 1:
                            quantity = float(row[2]) if row[2] else 1.0  # Assuming column B contains quantity
                        # Create the order line for the found product
                        order_line_model.create({
                            'sequence': iterator,  # Link to the selected sale order
                            'order_id': order.id,  # Link to the selected sale order
                            'product_id': product.id,
                            'name': product.display_name,  # Use the product name
                            'product_uom_qty': quantity,  # Use quantity from the file (or default 1)
                            'price_unit': product.list_price,  # Default price, could be modified
                            'product_uom': product.uom_id.id,  # Set the UoM for the product
                        })


            elif wizard.file_ods:
                file_path = '/opt/odoo/addons/net_diffusion/static/src/import.ods'

                if wizard.file_ods:
                    # Decode the base64 binary data
                    binary_data = base64.b64decode(wizard.file_ods)

                    # Write the binary content to the specified file path
                    try:
                        with open(file_path, 'wb') as file:
                            file.write(binary_data)
                    except Exception as e:
                        return {
                            'status': 'error',
                            'message': f'Error writing file: {str(e)}'
                        }

                    # Load the ODS file
                    doc = load(file_path)
                    # Find the first table
                    table = doc.getElementsByType(Table)[0]

                    iterator = 0
                    # Iterate through rows in the sheet, assuming the barcode is in column A (index 1)
                    last_line = order_line_model.search([('order_id', '=', order.id), ('is_delivery', '=', False)],
                                                        limit=1, order="sequence desc")
                    if last_line:
                        iterator = last_line.sequence
                        # raise ValidationError(iterator)
                    # Iterate over the rows
                    for row in table.getElementsByType(TableRow):

                        iterator += 1
                        # Extract cells from the row
                        cells = row.getElementsByType(TableCell)

                        # Get the first and third column value (if they exist)
                        if len(cells) > 2:  # Ensure that the row has at least 3 columns
                            first_cell_value = wizard.get_cell_value(cells[0])
                            third_cell_value = wizard.get_cell_value(cells[2])

                        product = product_model.search([('barcode', '=', first_cell_value.strip())], limit=1)
                        if not product and re.match(pattern, barcode):
                            isbn_db_data = self.fetch_from_isbndb(first_cell_value.strip())
                            # google_books_data = self.fetch_from_google_books(barcode)
                            # open_library_data = self.fetch_from_open_library(barcode)
                            product_template = product_template.create({
                                'barcode': barcode,
                                'name': isbn_db_data['data'].get('book').get('title_long'),
                                'dilicom_url': isbn_db_data['data'].get('book').get('image'),
                                'dilicom_url_thumb': isbn_db_data['data'].get('book').get('image'),
                                'editeur': isbn_db_data['data'].get('book').get('publisher'),
                                'auteur': isbn_db_data['data'].get('book').get('authors'),
                                'description_ecommerce': isbn_db_data['data'].get('book').get('synopsis'),
                                'default_code': barcode,
                                'type': 'product',
                                'import_state': True,
                            })
                            product = product_template.product_variant_id

                        pquantity = 1
                        if product:
                            if third_cell_value:
                                pquantity = float(
                                    third_cell_value) if third_cell_value else 1.0  # Assuming column B contains quantity
                            # Create the order line for the found product
                            order_line_model.create({
                                'sequence': iterator,  # Link to the selected sale order
                                'order_id': order.id,  # Link to the selected sale order
                                'product_id': product.id,
                                'name': product.display_name,  # Use the product name
                                'product_uom_qty': pquantity,  # Use quantity from the file (or default 1)
                                'price_unit': product.list_price,  # Default price, could be modified
                                'product_uom': product.uom_id.id,  # Set the UoM for the product
                            })

        return True
