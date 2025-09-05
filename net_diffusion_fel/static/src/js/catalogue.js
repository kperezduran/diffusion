/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';
import {renderToElement} from "@web/core/utils/render";

publicWidget.registry.cataloguePage = publicWidget.Widget.extend({
    selector: '.catalogue_page',
    events: {
        'click .catalogue_submit_button ': '_searchAjax',
        'keypress .catalogue_search_container input, keypress .catalogue_search_container select': '_onKeyPress',
    },

    start() {
        this._super(...arguments);
        this._loadCategories();
        this._initDateRangePicker();
        // Optionally trigger initial search
        // this._searchAjax();
    },
    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm");
        this.selectedCategoryId = null;
        this.catPage = { 'root': 0 }; // pagination offsets per parent id
        this.catBatch = 10; // show 10 categories at a time
        // bind form submit to trigger search
        const form = document.querySelector('.catalogue_search_container');
        if (form) {
            form.addEventListener('submit', (ev) => { ev.preventDefault(); this._searchAjax(); });
        }
    },
    _onKeyPress: async function (event) {
        if (event.key === 'Enter') {
            this._searchAjax();
        }
    },
    _searchAjax: async function () {
        // ensure date_from/date_to are synced from the date range input if any
        this._syncDateRangeHiddenFields();
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
            page: 1, limit: 9,
        };
        const result = await this.rpc('/catalogue-ajax', payload);
        if (result && result.products) {
            // map types for display
            result.products.forEach(livre => {
                livre['type_livre'] = this._process_type_book(livre['type_livre']);
            });

            const container = document.querySelector('.catalogue_products_container');
            const newHTML = $(renderToElement('net_diffusion_fel.products_ajax', {
                products: result.products,
            }));
            container.outerHTML = newHTML[0].outerHTML;

            // append Load More button if more results
            document.querySelectorAll('.load_more_btn').forEach(b => b.remove());
            if (result.pager && (result.pager.remaining || result.pager.more || (result.pager.total > (result.pager.offset + result.pager.step)))) {
                this._appendLoadMore(result, payload);
            }
        }
    },

    _initDateRangePicker: function () {
        const input = document.getElementById('catalogue_date_range');
        if (!input) return;
        const hiddenFrom = document.querySelector("input[name='date_from']");
        const hiddenTo = document.querySelector("input[name='date_to']");
        const updateHidden = (dates) => {
            if (dates && dates.length) {
                const fmt = (d) => d.toISOString().slice(0, 10);
                if (dates.length === 1) {
                    hiddenFrom.value = fmt(dates[0]);
                    hiddenTo.value = '';
                } else {
                    const [d1, d2] = dates;
                    const from = d1 <= d2 ? d1 : d2;
                    const to = d1 <= d2 ? d2 : d1;
                    hiddenFrom.value = fmt(from);
                    hiddenTo.value = fmt(to);
                }
            } else {
                hiddenFrom.value = '';
                hiddenTo.value = '';
            }
        };
        // Try to use flatpickr if available (Odoo 17 uses it in webclient)
        if (window.flatpickr) {
            try {
                window.flatpickr(input, {
                    mode: 'range',
                    dateFormat: 'Y-m-d',
                    allowInput: true,
                    onChange: function (selectedDates) {
                        updateHidden(selectedDates);
                    },
                });
                return;
            } catch (e) {
                // fallthrough
            }
        }
        // Fallback: basic parser "YYYY-MM-DD to YYYY-MM-DD"
        input.addEventListener('change', () => this._syncDateRangeHiddenFields());
    },

    _syncDateRangeHiddenFields: function () {
        const input = document.getElementById('catalogue_date_range');
        if (!input) return;
        const hiddenFrom = document.querySelector("input[name='date_from']");
        const hiddenTo = document.querySelector("input[name='date_to']");
        const val = (input.value || '').trim();
        if (!val) {
            hiddenFrom.value = '';
            hiddenTo.value = '';
            return;
        }
        // Try flatpickr selected dates via dataset (if any)
        if (input._flatpickr && input._flatpickr.selectedDates) {
            const dates = input._flatpickr.selectedDates;
            if (dates.length) {
                const fmt = (d) => d.toISOString().slice(0, 10);
                if (dates.length === 1) {
                    hiddenFrom.value = fmt(dates[0]);
                    hiddenTo.value = '';
                } else {
                    const [d1, d2] = dates;
                    const from = d1 <= d2 ? d1 : d2;
                    const to = d1 <= d2 ? d2 : d1;
                    hiddenFrom.value = fmt(from);
                    hiddenTo.value = fmt(to);
                }
                return;
            }
        }
        // Parse text pattern
        const parts = val.split(/\s+to\s+|\s+-\s+|\s+au\s+/i);
        if (parts.length === 2) {
            hiddenFrom.value = parts[0];
            hiddenTo.value = parts[1];
        } else {
            hiddenFrom.value = val;
            hiddenTo.value = '';
        }
    },

    _appendLoadMore: function (result, basePayload) {
        const container = document.querySelector('.catalogue_products_container');
        if (!container) return;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-outline-primary w-100 load_more_btn mt-3';
        btn.textContent = 'Charger plus';
        btn.onclick = async () => {
            // next page calculation
            const nextOffset = (result.pager && result.pager.offset ? result.pager.offset : 0) + (result.pager && result.pager.step ? result.pager.step : (basePayload.limit || 9));
            const page = Math.floor(nextOffset / (basePayload.limit || 9)) + 1;
            const payload = Object.assign({}, basePayload, {page});
            const resp = await this.rpc('/catalogue-ajax', payload);
            if (resp && resp.products && resp.products.length) {
                resp.products.forEach(livre => {
                    livre['type_livre'] = this._process_type_book(livre['type_livre']);
                });
                const frag = renderToElement('net_diffusion_fel.products_ajax', {products: resp.products});
                // append children inside container (skip wrapper)
                Array.from(frag.querySelectorAll('.catalogue_product_item')).forEach(node => container.appendChild(node));
                // update pager
                result = resp; // reuse variable for simplicity
                // if no more, remove button
                if (!(resp.pager && (resp.pager.remaining || resp.pager.more || (resp.pager.total > (resp.pager.offset + resp.pager.step))))) {
                    btn.remove();
                }
            } else {
                btn.remove();
            }
        };
        container.parentNode.appendChild(btn);
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
    _loadCategories: async function (parentId=null, append=false) {
        const tree = document.getElementById('catalogue_category_tree');
        if (!tree) return;
        const payload = parentId ? {parent_id: parentId} : {};
        const cats = await this.rpc('/catalogue/categories', payload);
        // Determine container UL
        let containerUL;
        if (parentId) {
            const parentLi = tree.querySelector(`li[data-cat-id="${parentId}"]`);
            if (!parentLi) return;
            containerUL = parentLi.querySelector('ul');
            if (!containerUL) {
                containerUL = document.createElement('ul');
                parentLi.appendChild(containerUL);
            } else if (!append) {
                containerUL.innerHTML = '';
            }
        } else {
            tree.innerHTML = '';
            containerUL = document.createElement('ul');
            tree.appendChild(containerUL);
        }
        // Pagination slices
        const key = parentId || 'root';
        const start = this.catPage[key] || 0;
        const end = start + this.catBatch;
        const slice = cats.slice(0, end);
        containerUL.innerHTML = '';
        slice.forEach(cat => containerUL.appendChild(this._renderCategoryNode(cat)));
        // Show more
        if (cats.length > end) {
            const more = document.createElement('li');
            const moreBtn = document.createElement('span');
            moreBtn.className = 'show_more_cat';
            moreBtn.textContent = 'Afficher plus';
            moreBtn.onclick = () => {
                this.catPage[key] = end;
                this._loadCategories(parentId, true);
            };
            more.appendChild(moreBtn);
            containerUL.appendChild(more);
        }
    },
    _renderCategoryNode: function (cat) {
        const li = document.createElement('li');
        li.className = 'catalogue_cat_node';
        li.setAttribute('data-cat-id', String(cat.id));
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
            // show children automatically if any
            if (cat.has_children) {
                this._loadCategories(cat.id);
            }
            // trigger search
            this._searchAjax();
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
                    // use paginated loader
                    await this._loadCategories(cat.id);
                    caret.textContent = '▾';
                }
            };
        }
        return li;
    }
});
