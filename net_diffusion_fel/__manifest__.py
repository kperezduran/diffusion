# -*- coding: utf-8 -*-
{
    'name': 'NET-EASY Diffusion FEL',
    'category': 'Website/Website',
    'sequence': 202,
    'website': '',
    'summary': 'FEL features for NET-EASY Diffusion',
    'version': '1.0',
    'description': """
        FEL features for NET-EASY Diffusion.
        Provides an ajaxified /catalogue page with search and category tree.
    """,
    'depends': ['net_diffusion'],
    'application': True,
    'license': 'LGPL-3',
    'data': [
        'views/catalogue_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'net_diffusion/static/lib/swiperjs/swiper-element-bundle.min.js',
            'net_diffusion_fel/static/src/css/catalogue.css',
            'net_diffusion_fel/static/src/js/catalogue.js',
            'net_diffusion_fel/static/src/js/net_slider_loader.js',
            'net_diffusion_fel/static/src/xml/catalogue_ajax.xml',
        ],
    },
}