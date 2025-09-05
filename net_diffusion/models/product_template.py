from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.addons.http_routing.models.ir_http import slugify
from odoo.http import request
from odoo.exceptions import UserError, ValidationError


class ProductTagCategory(models.Model):
    _name = 'product.tag_category'
    _order = "sequence asc"

    name = fields.Char('nom')
    sequence = fields.Integer('sequence')
    tag_ids = fields.One2many('product.tag', 'categ_id', string='Product Tags')


class ProductTag(models.Model):
    _inherit = 'product.tag'

    categ_id = fields.Many2one('product.tag_category', string='Tag Category')


class WebsiteSliderCategory(models.Model):
    _name = 'website.an_slider_category'
    _description = "Slider Category"

    name = fields.Char('Nom')
    slider_product_ids = fields.One2many('website.an_slider_products', 'categ_id', string='Sliders products')
    website_sequence = fields.Integer('Website Sequence', help="Determine the display order in the Website E-commerce",
                                      default=1)


class WebsiteSliderProduct(models.Model):
    _name = 'website.an_slider_product'
    _description = "Slider Item Product"
    _order = "sequence asc"

    sequence = fields.Integer('Sequence', default=1)
    product_id = fields.Many2one('product.template', string="Produits")
    slider_id = fields.Many2one('website.an_slider_products', string="Slider")


class WebsiteSliderProducts(models.Model):
    _name = 'website.an_slider_products'
    _description = "Slider Product Mgnt"
    _order = "website_sequence asc"

    def _active_languages(self):
        return self.env['res.lang'].search([]).ids

    def _default_language(self):
        lang_code = self.env['ir.default']._get('res.partner', 'lang')
        def_lang_id = self.env['res.lang']._lang_get_id(lang_code)
        return def_lang_id or self._active_languages()[0]

    name = fields.Char('Nom')
    title = fields.Char('Titre', translate=True)
    slider_text = fields.Text('Text slider', translate=True)

    publish = fields.Boolean('Publié', default=False)
    website_ids = fields.Many2many('website', 'website_ansliderp_rel', 'website_id', 'slider_id', 'Website',
                                   default=None)
    date_from = fields.Datetime(string='Date début')
    date_to = fields.Datetime(string='Date fin')
    website_sequence = fields.Integer('Website Sequence', help="Determine the display order in the Website E-commerce",
                                      default=1)
    slider_product_ids = fields.One2many('website.an_slider_product', 'slider_id', string='Slider item')
    language_ids = fields.Many2many('res.lang', 'lang_sliderp_rel', 'slider_id', 'lang_id', string="Languages",
                                    default=_active_languages)
    categ_id = fields.Many2one('website.an_slider_category', string="Catégorie")