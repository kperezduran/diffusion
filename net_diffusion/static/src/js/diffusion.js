/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';
import {renderToElement} from "@web/core/utils/render";

publicWidget.registry.websiteSaleTags = publicWidget.Widget.extend({
    selector: '.js_sale',
    events: {
        'input .js_editor_tags': '_debouncedOnChangeEditor',
        'input .js_author_tags': '_debouncedOnChangeAuthor',
        'input .js_collection_tags': '_debouncedOnChangeCollection',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm");
        // Create debounced versions of the change handlers
        this._debouncedOnChangeAuthor = this._debounce(this._onChangeAuthor.bind(this), 500);
        this._debouncedOnChangeEditor = this._debounce(this._onChangeEditor.bind(this), 500);
        this._debouncedOnChangeCollection = this._debounce(this._onChangeCollection.bind(this), 500);
    },

    // Debounce function to limit the rate at which a function can fire
    _debounce: function (func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    },

    _onChangeEditor: async function (ev) {
        ev.preventDefault();
        var elem = ev.target;
        var search = elem.value;
        if (search.length > 2) {
            var tag_list = elem.parentElement.nextElementSibling;
            var result = await this.rpc('/get/tags_editor', {
                'search': search,
            });
            if (result && tag_list.outerHTML) {
                var newHTML = $(renderToElement('net_diffusion.tags_editeur_filter', {
                    items: result,
                }));

                tag_list.outerHTML = newHTML[0].outerHTML;
            }
        }
    },
    _onChangeAuthor: async function (ev) {
        console.log('event');
        ev.preventDefault();
        var elem = ev.target;
        var search = elem.value;
        if (search.length > 2) {
            var tag_list = elem.parentElement.nextElementSibling;
            var result = await this.rpc('/get/tags_author', {
                'search': search,
            });
            if (result && tag_list.outerHTML) {
                var newHTML = $(renderToElement('net_diffusion.tags_auteur_filter', {
                    items: result,
                }));

                tag_list.outerHTML = newHTML[0].outerHTML;
            }
        }
    },
    _onChangeCollection: async function (ev) {
        console.log('event');
        ev.preventDefault();
        var elem = ev.target;
        var search = elem.value;
        if (search.length > 2) {
            var tag_list = elem.parentElement.nextElementSibling;
            var result = await this.rpc('/get/tags_collection', {
                'search': search,
            });
            if (result && tag_list.outerHTML) {
                var newHTML = $(renderToElement('net_diffusion.tags_collection_filter', {
                    items: result,
                }));

                tag_list.outerHTML = newHTML[0].outerHTML;
            }
        }
    },
});

publicWidget.registry.websiteSliders = publicWidget.Widget.extend({
    selector: '.homepage',

    start() {
        // swiper element
        const swipers = document.querySelectorAll('swiper-container.mySwiper');
        swipers.forEach(swiperEl => {
            // swiper parameters
            const swiperParams = {

                navigation: true,
                spaceBetween: 100,
                slidesPerView: 1,
                breakpoints: {
                    768: {
                        slidesPerView: 6,
                    },
                },
                on: {
                    init() {
                    },
                },
            };

            // now we need to assign all parameters to Swiper element
            Object.assign(swiperEl, swiperParams);

            // and now initialize it
            swiperEl.initialize();
        });
    },
});

publicWidget.registry.fastCartPage = publicWidget.Widget.extend({
    selector: '.fast_cart_page',
    events: {
        'click .fa-plus, .fa-minus': '_onChangeQty',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm");
    },
    // Helper function to format currency
    formatCurrency: function (amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'EUR'  // Specify the EUR currency code
        }).format(amount);

    },
    _onChangeQty: async function (ev) {
        var elem = ev.target;
        var line_id = elem.dataset.lineid;
        var new_qty = elem.dataset.qty;
        var product_id = elem.dataset.productid;
        var result = await this.rpc('/shop/cart/update_json', {
            'line_id': parseInt(line_id),
            'set_qty': new_qty,
            'product_id': parseInt(product_id),
        });
        if (result) {
            var qty_container = elem.parentElement;
            var row = qty_container.parentElement.parentElement;
            if (result['quantity'] == 0) {
                row.remove();
            } else {

                var minus = qty_container.querySelector('.fa-minus');
                var qty = qty_container.querySelector('.qty_value');
                var plus = qty_container.querySelector('.fa-plus');
                var price_subtotal = row.querySelector('.price_subtotal');
                var price_unit = row.querySelector('.price_unit');
                minus.dataset.qty = result['quantity'] - 1;
                qty.innerText = result['quantity'];
                plus.dataset.qty = result['quantity'] + 1;
                price_subtotal.innerText = (result['quantity'] * parseFloat(price_unit.innerText)).toFixed(2);

                var result = await this.rpc('/get/total_order');
                if (result) {
                    var order = result;
                    order.amount_untaxed = this.formatCurrency(order.amount_untaxed);
                    order.amount_tax = this.formatCurrency(order.amount_tax);
                    order.amount_total = this.formatCurrency(order.amount_total);

                    var summary = document.querySelector('.fast_cart_summary');
                    var newHTML = $(renderToElement('net_diffusion.dynamic_summary', {
                        website_sale_order: result,

                    }));
                    summary.outerHTML = newHTML[0].outerHTML;

                }
            }
        }
    },
});
