import os
import paramiko
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    supplier = fields.Many2one("res.partner", compute='_compute_infos_line', string="Fournisseur")
    editeur = fields.Char(string="Editeur", related="product_id.product_tmpl_id.editeur")
    code_dispo = fields.Char(string="Code disponibilité", related="product_id.product_tmpl_id.code_disponibility")
    date_parution = fields.Date(string="Date de parution", related="product_id.product_tmpl_id.date_parution")
    barcode = fields.Char(string="EAN", related="product_id.barcode")

    def _compute_infos_line(self):
        for record in self:
            if record.product_id:
                if record.product_id.variant_seller_ids:
                    record.supplier = record.product_id.variant_seller_ids[0].partner_id.id
                else:
                    record.supplier = None
            else:
                record.supplier = None


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    total_qty = fields.Integer(compute='_compute_total_qty', string="Total articles")
    state = fields.Selection(selection_add=[('drop', 'Dédiée')])
    sale_order_id = fields.Many2one('sale.order', string="Commande client", ondelete="set null")
    dilicom_purcharse = fields.Boolean(string="Commande Dilicom", default=True)
    is_dedie = fields.Boolean(string="Est une commande dédiée", default=False)
    dedie_partner = fields.Many2one("res.partner", string="Client", related="sale_order_id.partner_id")

    def open_purchase_order_form(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Commande Fournisseur',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',  # Ouvre dans la page courante
        }
    
    def button_confirm(self):
        for order in self:

            if order.state == 'drop':
                if not order.partner_id.gencode or not order.dilicom_purcharse:
                    continue
                order.is_dedie = True
                order.state = 'draft'
            res = super(PurchaseOrder, self).button_confirm()
            if order.dilicom_purcharse:
                self._generate_and_send_csv()
            return res

    def _compute_total_qty(self):
        for record in self:
            qty = 0
            if record.order_line:
                for line in record.order_line:
                    qty += line.product_qty
            record.total_qty = qty

    def _generate_and_send_csv(self):
        for order in self:

            if not order.partner_id.gencode or not order.dilicom_purcharse:
                continue
            file_name = f"purchase_order_{order.name}.txt"
            file_path = f"/opt/odoo/addons/net_diffusion/static/src/doc/commandes/{file_name}"

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, mode='w', encoding='utf-8') as file:
                # Write each line as plain text
                file.write(f"A0001{order.partner_id.gencode}\n")
                file.write(f"B0002{order.company_id.partner_id.ref}\n")
                file.write(f"C0003{order.name}\n")
                file.write(f"D0004{order.write_date.strftime('%Y%m%d')}\n")
                file.write("E0005090\n")
                file.write("G00060\n")

                iterator = 7
                # Lines for each purchase line with barcode and quantity
                for line in order.order_line:
                    order_line_row = f"L{str(iterator).zfill(4)}{line.product_id.barcode}{str(int(line.product_qty)).zfill(5)}"
                    file.write(order_line_row + "\n")
                    iterator += 1

                # Final line
                file.write(f"Q{str(iterator).zfill(4)}\n")
            self._sftp_send_file(file_path, file_name)

    def _sftp_send_file(self, file_path, file_name):
        host = 'ftpack.centprod.com'
        port = 10022
        username = 'DFA00051'
        password = ';.0cicm"OYn1'

        try:
            _logger.info('Starting SFTP transfer for file: %s', file_name)
            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)

            with paramiko.SFTPClient.from_transport(transport) as sftp:
                sftp.put(file_path, f'/I/{file_name}')
                _logger.info('CSV file successfully sent via SFTP: %s', file_name)

        except Exception as e:
            _logger.error('Failed to send CSV via SFTP: %s', str(e))
        finally:
            transport.close()
