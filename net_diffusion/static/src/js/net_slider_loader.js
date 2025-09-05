/** Net Slider dynamic loader for Odoo 17 (OWL/RPC JSON)**/
odoo.define('net_diffusion.net_slider_loader', function (require) {
    'use strict';

    const { jsonRpc } = require('web.rpc');

    async function fetchInjections() {
        try {
            const url = window.location.pathname + window.location.search;
            return await jsonRpc('/net_slider/config', 'call', { url });
        } catch (e) {
            console.warn('NetSlider config error', e);
            return [];
        }
    }

    async function fetchHTML(id) {
        try {
            const resp = await jsonRpc(`/net_slider/render/${id}`, 'call', {});
            return (resp && resp.html) || '';
        } catch (e) {
            console.warn('NetSlider render error', e);
            return '';
        }
    }

    async function init() {
        const injections = await fetchInjections();
        if (!injections || !injections.length) return;
        for (const inj of injections) {
            const target = document.querySelector(inj.css_selector);
            if (!target) continue;
            const html = await fetchHTML(inj.id);
            if (!html) continue;
            const container = document.createElement('div');
            container.className = 'net-slider-injected';
            container.innerHTML = html;
            target.appendChild(container);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
});
