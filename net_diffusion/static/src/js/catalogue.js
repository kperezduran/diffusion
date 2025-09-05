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
        this._loadCategories();
        // Optionally trigger initial search
        // this._searchAjax();
    },
    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm");
        this.selectedCategoryId = null;
    },
    _onKeyPress: async function (event) {
        if (event.key === 'Enter') {
            this._searchAjax();
        }
    },
    _searchAjax: async function () {
        const title = document.querySelector("input[name='title']").value;
        const auteur = document.querySelector("input[name='editor']").value;
        const editeur = document.querySelector("input[name='author']").value;
        const collection = document.querySelector("input[name='collection']").value;
        const ean = document.querySelector("input[name='ean']").value;
        const disponibility = document.querySelector("select[name='disponility']").value;
        const date_from = document.querySelector("input[name='date_from']")?.value || '';
        const date_to = document.querySelector("input[name='date_to']")?.value || '';
        const category_id = this.selectedCategoryId || null;

        const payload = {
            title, auteur, editeur, collection, ean, disponibility, date_from, date_to, category_id,
        };
        const result = await this.rpc('/catalogue-ajax', payload);
        if (result && result.products) {
            // map types for display
            result.products.forEach(livre => {
                livre['type_livre'] = this._process_type_book(livre['type_livre']);
            });

            const container = document.querySelector('.catalogue_products_container');
            const newHTML = $(renderToElement('net_diffusion.products_ajax', {
                products: result.products,
            }));
            container.outerHTML = newHTML[0].outerHTML;
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
    },
    _loadCategories: async function () {
        const tree = document.getElementById('catalogue_category_tree');
        if (!tree) return;
        const roots = await this.rpc('/catalogue/categories', {});
        tree.innerHTML = '';
        const ul = document.createElement('ul');
        roots.forEach(cat => ul.appendChild(this._renderCategoryNode(cat)));
        tree.appendChild(ul);
    },
    _renderCategoryNode: function (cat) {
        const li = document.createElement('li');
        li.className = 'catalogue_cat_node';
        const caret = document.createElement('span');
        caret.className = 'caret' + (cat.has_children ? '' : ' disabled');
        caret.textContent = cat.has_children ? '▸' : '';
        const label = document.createElement('span');
        label.className = 'label';
        label.textContent = cat.name;
        label.style.cursor = 'pointer';
        label.onclick = () => {
            this.selectedCategoryId = cat.id;
            // highlight selection
            document.querySelectorAll('#catalogue_category_tree .label').forEach(el => el.classList.remove('selected'));
            label.classList.add('selected');
        };
        li.appendChild(caret);
        li.appendChild(label);
        if (cat.has_children) {
            caret.style.cursor = 'pointer';
            caret.onclick = async () => {
                if (li.querySelector('ul')) {
                    // toggle
                    const ul = li.querySelector('ul');
                    ul.style.display = ul.style.display === 'none' ? 'block' : 'none';
                    caret.textContent = ul.style.display === 'none' ? '▸' : '▾';
                } else {
                    const children = await this.rpc('/catalogue/categories', {parent_id: cat.id});
                    const ul = document.createElement('ul');
                    children.forEach(ch => ul.appendChild(this._renderCategoryNode(ch)));
                    li.appendChild(ul);
                    caret.textContent = '▾';
                }
            };
        }
        return li;
    }
});
