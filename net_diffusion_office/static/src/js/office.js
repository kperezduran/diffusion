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

            // Show success message (Bootstrap 5 compatible)
            const alert = document.createElement('div');
            alert.className = 'alert alert-success alert-dismissible fade show';
            alert.setAttribute('role', 'alert');
            alert.textContent = _t('Product added to cart.');
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn-close';
            btn.setAttribute('data-bs-dismiss', 'alert');
            btn.setAttribute('aria-label', 'Close');
            alert.appendChild(btn);

            card?.appendChild(alert);

            setTimeout(() => {
                // Manually remove if not already closed by user
                if (alert && alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 3000);
        } catch (e) {
            // no-op; optionally log
        }
    },
});

export default publicWidget.registry.OfficeWidget;