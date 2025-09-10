/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';
import {renderToElement} from "@web/core/utils/render";

publicWidget.registry.cataloguePage = publicWidget.Widget.extend({
    selector: '.catalogue_page',
    events: {
        'click .catalogue_submit_button ': '_searchAjax',
        'keypress .catalogue_search_container div input': '_onKeyPress',
    },

    start() {
        this._super(...arguments);
        // this._searchAjax();
    },
    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm");
    },
    _onKeyPress: async function (event) {
        if (event.key === 'Enter') {
            this._searchAjax();
        }
    },
    _searchAjax: async function () {
        var title = document.querySelector("input[name='title']").value;
        var auteur = document.querySelector("input[name='editor']").value;
        var editeur = document.querySelector("input[name='author']").value;
        var collection = document.querySelector("input[name='collection']").value;
        var ean = document.querySelector("input[name='ean']").value;
        var disponibility = document.querySelector("select[name='disponility']").value;

        var result = await this.rpc('/catalogue-ajax', {
            'title': title,
            'auteur': auteur,
            'editeur': editeur,
            'collection': collection,
            'ean': ean,
            'disponibility': disponibility,
        });
        if (result) {
            console.log(result);
            result.forEach(livre => {
                livre['type_livre'] = this._process_type_book(livre['type_livre']);
            });

            var catalogue_products_container = document.querySelector('.catalogue_products_container');

            var newHTML = $(renderToElement('net_diffusion.products_ajax', {
                products: result,

            }));
            catalogue_products_container.outerHTML = newHTML[0].outerHTML;


        }
    },
    _process_type_book: function (type) {
        const typeMap = {
            'R': 'Relié',
            'B': 'Broché',
            'P': 'Poche',
            'J': 'Jeux',
            'D': 'Disque vinyle',
            'DC': 'Disque compact',
            'DV': 'Dique vidéo, DVD',
            'CD': 'CD-rom',
            'LD': 'Livre disque',
            'K': 'Cassette',
            'KA': 'Cassette Audio',
            'KV': 'Cassette vidéo',
            'LK': 'Livre cassette',
            'C': 'Cuir',
            'E': 'Etui',
            'L': 'Luxe',
            'X': 'Journal, revue',
            'SM': 'Support magnétique',
            'DI': 'Diapositives',
            'PC': 'Publicité',
            'AL': 'Album',
            'CR': 'Cartes routières',
            'PO': 'Posters',
            'CA': 'Calendriers',
            'O': 'Objet',
            'N': 'Contenu numérique',
        };

        return typeMap[type] || '';
    }
});
