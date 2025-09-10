/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';
import { _t } from '@web/core/l10n/translation';

publicWidget.registry.OfficeWidget = publicWidget.Widget.extend({
    selector: '.js_office',
    events: {
        'click .js_add_cart_json': '_onAddToCart',
    },

    start() {
        return this._super(...arguments);
    },

    _showCartPopover(anchorEl, data) {
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

            // Content
            const title = card.querySelector('.catalogue_product_title span,a span')?.textContent || _t('Produit');
            const price = card.querySelector('.catalogue_product_item_price')?.textContent?.trim() || '';
            const qty = data?.cart_quantity;
            pop.innerHTML = `
                <div class="d-flex align-items-start gap-2">
                    <div class="flex-grow-1">
                        <div class="fw-semibold">${_t('Ajouté au panier')}</div>
                        <div class="small text-muted text-truncate" title="${title}">${title}</div>
                        ${price ? `<div class="small">${_t('Prix')}: ${price}</div>` : ''}
                        ${qty ? `<div class="small text-muted">${_t('Articles dans le panier')}: ${qty}</div>` : ''}
                    </div>
                    <div class="text-primary"><i class="dri dri-cart"></i></div>
                </div>`;

            document.body.appendChild(pop);
            // Position near anchor (above-right), fallback to center if offscreen
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
            }, 2600);

            pop.addEventListener('click', () => {
                pop.style.opacity = '0';
                setTimeout(() => { if (pop.parentNode) pop.parentNode.removeChild(pop); }, 150);
            });
        } catch (err) {
            // ignore popover errors
        }
    },

    // Handlers
    async _onAddToCart(ev) {
        ev.preventDefault();
        const card = ev.currentTarget.closest('.card');
        const productId = card?.querySelector('input[name="product_id"]').value;
        const rpc = this.bindService('rpc');

        try {
            const data = await rpc('/shop/cart/update_json', {
                product_id: parseInt(productId),
                add_qty: 1,
            });

            if (data?.cart_quantity) {
                const navButton = document.querySelector('header .o_wsale_my_cart');
                if (navButton) {
                    const qtyEl = navButton.querySelector('.my_cart_quantity');
                    const current = parseInt(qtyEl?.textContent || '0') || 0;
                    qtyEl.textContent = String(current + 1);
                }
            }

            // UX feedback popover is handled by FEL catalogue widget (catalogue.js) when present.
            // Intentionally no popover here to avoid duplication on /catalogue.
        } catch (e) {
            // no-op; optionally log
        }
    },
});

export default publicWidget.registry.OfficeWidget;