# -*- coding: utf-8 -*-
{
    'name': 'NET-EASY Diffusion Office',
    'category': 'Website/Website',
    'sequence': 201,
    'website': '',
    'summary': 'Office management for Diffusion',
    'version': '1.0',
    'description': """
        This module adds office management functionality to Diffusion.
        It allows creating and managing offices with date limits, delivery dates, themes, and names.
        Offices are linked to product categories and can generate products with code_disponibility = 2.
    """,
    'depends': ['website_sale', 'stock', 'purchase', 'net_diffusion'],
    'application': True,
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/office_views.xml',
        'views/office_category_views.xml',
        'views/office_templates.xml',
        'views/office_order_views.xml',
        'views/office_order_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'net_diffusion_office/static/src/css/office.css',
            'net_diffusion_office/static/src/js/office.js',
        ],
    },
}