/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';
import {renderToElement} from "@web/core/utils/render";

publicWidget.registry.cataloguePage = publicWidget.Widget.extend({
    selector: '.catalogue_page',
    events: {
        'click .catalogue_submit_button ': '_searchAjax',
        'keypress .catalogue_search_container input, keypress .catalogue_search_container select': '_onKeyPress',
        'click .js_add_cart_json': '_onAddToCartClick',
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
            const newEl = renderToElement('net_diffusion_fel.products_ajax', {
                products: result.products,
            });
            container.outerHTML = newEl.outerHTML;

            // append Load More button if more results
            document.querySelectorAll('.load_more_btn').forEach(b => b.remove());
            if (result.pager && (result.pager.remaining || result.pager.more || (result.pager.total > (result.pager.offset + result.pager.step)))) {
                this._appendLoadMore(result, payload);
            }
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
            const nextOffset = (result.pager && result.pager.offset ? result.pager.offset : 0) + (result.pager && result.pager.step ? result.pager.step : (basePayload.limit || 18));
            const page = Math.floor(nextOffset / (basePayload.limit || 18)) + 1;
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
                // try to set caret expanded
                caret.textContent = '▾';
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
    },

    _onAddToCartClick: function (ev) {
        // Do not prevent default; OfficeWidget handles RPC. Just show local popover feedback.
        const anchor = ev.currentTarget;
        this._showCartPopover(anchor);
    },

    _showCartPopover(anchorEl) {
        try {
            const anchor = anchorEl instanceof HTMLElement ? anchorEl : null;
            const card = anchor?.closest('.catalogue_product_item') || anchor?.closest('.card') || document.body;
            // Build popover container
            const pop = document.createElement('div');
            pop.className = 'fel-cart-popover shadow';
            pop.setAttribute('role', 'status');
            pop.style.position = 'fixed';
            pop.style.zIndex = '1080';
            pop.style.minWidth = '220px';
            pop.style.maxWidth = '320px';
            pop.style.background = '#ffffff';
            pop.style.border = '1px solid rgba(0,0,0,.1)';
            pop.style.borderRadius = '.5rem';
            pop.style.padding = '.75rem 1rem';
            pop.style.boxShadow = '0 .5rem 1rem rgba(0,0,0,.15)';
            pop.style.opacity = '0';
            pop.style.transition = 'opacity .15s ease-out, transform .2s ease-out';
            pop.style.transform = 'translateY(-6px)';

            // Content from card
            const title = card.querySelector('.catalogue_product_title span,a span')?.textContent || 'Produit';
            const price = card.querySelector('.catalogue_product_item_price')?.textContent?.trim() || '';
            pop.innerHTML = `
                <div class="d-flex align-items-start gap-2">
                    <div class="flex-grow-1">
                        <div class="fw-semibold">Ajouté au panier</div>
                        <div class="small text-muted text-truncate" title="${title}">${title}</div>
                        ${price ? `<div class="small">Prix: ${price}</div>` : ''}
                    </div>
                    <div class="text-primary"><i class="dri dri-cart"></i></div>
                </div>`;

            document.body.appendChild(pop);
            // Position near anchor (above-right), fallback if offscreen
            const rect = anchor?.getBoundingClientRect();
            const viewportW = window.innerWidth;
            const viewportH = window.innerHeight;
            let top = (rect?.top ?? viewportH / 2) - 10;
            let left = (rect?.right ?? viewportW / 2) - 10;
            // adjust to keep fully visible
            const pw = 280; // approx
            const ph = 120; // approx
            if (left + pw > viewportW - 10) left = viewportW - pw - 10;
            if (left < 10) left = 10;
            if (top + ph > viewportH - 10) top = viewportH - ph - 10;
            if (top < 10) top = 10;
            pop.style.top = `${top}px`;
            pop.style.left = `${left}px`;

            requestAnimationFrame(() => {
                pop.style.opacity = '1';
                pop.style.transform = 'translateY(0)';
            });

            const remove = () => { if (pop.parentNode) pop.parentNode.removeChild(pop); };
            setTimeout(() => {
                pop.style.opacity = '0';
                pop.style.transform = 'translateY(-6px)';
                setTimeout(remove, 200);
            }, 2200);

            pop.addEventListener('click', () => {
                pop.style.opacity = '0';
                setTimeout(() => { if (pop.parentNode) pop.parentNode.removeChild(pop); }, 150);
            });
        } catch (err) {
            // ignore popover errors
        }
    },
});
