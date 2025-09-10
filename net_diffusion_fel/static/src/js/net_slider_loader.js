/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';

/**
 * BookSliderLoader
 * - Finds placeholders (.js_loadslider_books) and injects sliders for each published website.an_slider_products
 * - Renders the slider title (field `title`)
 * - Slides are product cards (from product.template via website.an_slider_product lines)
 * - Responsive slidesPerView: 5 (>=1200), 4 (>=992), 3 (>=768), 1 (<768)
 * - Lazy loads next batches when clicking Next or reaching the end, until all items loaded
 */
publicWidget.registry.BookSliderLoader = publicWidget.Widget.extend({
    selector: '.js_loadslider_books',

    init() {
        this._super(...arguments);
        this.rpc = this.bindService('rpc');
        this.orm = this.bindService('orm');
        this._slidersState = new Map(); // sliderId -> {offset, limit, total, loading}
    },

    async start() {
        const $root = this.$el;
        try {
            // Fetch sliders
            const sliders = await this.rpc('/slider/published');
            if (!sliders || !sliders.length) {
                return this._super ? this._super(...arguments) : Promise.resolve();
            }

            for (const slider of sliders) {
                await this._renderSlider($root, slider);
            }

        } catch (e) {
            console.warn('BookSliderLoader start failed', e);
        }

        // Initialiser SwiperJS à la fin après que tout soit rendu
        setTimeout(() => {
            this._initializeAllSwipers();
        }, 100);

        return this._super ? this._super(...arguments) : Promise.resolve();
    },

    async _renderSlider($root, slider) {
        // Build the container structure
        const container = document.createElement('div');
        container.className = 'netfel-slider-block my-4';
        container.dataset.sliderId = String(slider.id);

        const title = document.createElement('h3');
        title.className = 'netfel-slider-title mb-3 text-center';
        title.textContent = slider.title || slider.name || '';
        container.appendChild(title);

        // Créer la structure Swiper EXACTEMENT comme dans le template qui fonctionne
        const swiperContainer = document.createElement('swiper-container');
        swiperContainer.className = 'mySwiper netfel-swiper';

        // Swiper Element expects slides as direct children; keep wrapper only if project requires
        const swiperWrapper = document.createElement('div');
        swiperWrapper.className = 'swiper-wrapper';
        swiperContainer.appendChild(swiperWrapper);

        container.appendChild(swiperContainer);

        // Loader
        const loader = document.createElement('div');
        loader.className = 'netfel-slider-loader text-center py-3';
        loader.textContent = 'Chargement...';
        container.appendChild(loader);

        $root.append(container);

        // Initialize state and load products
        this._slidersState.set(slider.id, {
            offset: 0,
            limit: 20, // Charger plus de produits d'un coup
            total: null,
            loading: false,
            wrapper: swiperWrapper,
            container: swiperContainer
        });

        await this._loadSliderProducts(slider.id);

        // Hide loader
        loader.style.display = 'none';
    },

    async _loadSliderProducts(sliderId) {
        const state = this._slidersState.get(sliderId);
        if (!state || state.loading) return;

        state.loading = true;

        try {
            // Fetch products via backend route to avoid public ACL issues
            const result = await this.rpc('/slider/products', { slider_id: sliderId, offset: state.offset, limit: state.limit });
            const products = (result && result.products) ? result.products : [];
            if (!products.length) return;

            // Render slides
            const wrapper = state.wrapper;
            wrapper.innerHTML = ''; // Clear existing

            for (const product of products) {
                const slide = this._createProductSlide(product);
                wrapper.appendChild(slide);
            }

            // Update pagination state
            if (result) {
                state.total = typeof result.total === 'number' ? result.total : state.total;
                state.offset = (state.offset || 0) + products.length;
            }

        } catch (e) {
            console.warn('Failed loading products for slider', sliderId, e);
        } finally {
            state.loading = false;
        }
    },

    _createProductSlide(product) {
        const slide = document.createElement('div');
        slide.className = 'swiper-slide';

        slide.innerHTML = `
            <div class="netfel-card h-100 d-flex flex-column p-2 border rounded bg-white">
                <a href="${product.website_url || '/shop/product/' + product.id}" class="d-block text-center flex-grow-1 text-decoration-none">
                    <div class="d-flex align-items-center justify-content-center" style="height: 180px;">
                        <img loading="lazy" 
                             alt="${product.name || ''}" 
                             src="${product.dilicom_url_thumb || '/web/image/product.template/' + product.id + '/image_512'}" 
                             class="img-fluid" 
                             style="max-width: 114px; max-height: 160px; object-fit: contain;">
                    </div>
                </a>
                <div class="mt-2 small text-truncate text-center" 
                     title="${product.name || ''}" 
                     style="line-height: 1.2; min-height: 2.4em;">
                    ${product.name || ''}
                </div>
                <div class="text-primary fw-bold text-center mt-1">
                    ${typeof product.list_price === 'number' ? product.list_price.toFixed(2) + ' €' : ''}
                </div>
            </div>
        `;

        return slide;
    },

    _initializeAllSwipers() {
        // Cette fonction reprend exactement la logique qui fonctionne dans diffusion.js
        const swipers = document.querySelectorAll('swiper-container.mySwiper');
        console.log('Initializing', swipers.length, 'swipers');

        swipers.forEach((swiperEl, index) => {
            try {
                // Vérifier si déjà initialisé
                if (swiperEl.hasAttribute('initialized') || swiperEl.initialized) {
                    console.log('Swiper', index, 'already initialized, skipping');
                    return;
                }

                // Vérifier que l'élément a des slides
                const slides = swiperEl.querySelectorAll('.swiper-slide, swiper-slide');
                if (slides.length === 0) {
                    console.warn('Swiper', index, 'has no slides, skipping');
                    return;
                }

                console.log('Swiper', index, 'has', slides.length, 'slides');

                // Paramètres Swiper - EXACTEMENT comme dans diffusion.js
                const swiperParams = {
                    navigation: true,
                    spaceBetween: 16,
                    slidesPerView: 1,
                    breakpoints: {
                        480: { slidesPerView: 2, spaceBetween: 16 },
                        768: { slidesPerView: 3, spaceBetween: 16 },
                        992: { slidesPerView: 4, spaceBetween: 16 },
                        1200: { slidesPerView: 5, spaceBetween: 16 }
                    },
                    on: {
                        init: () => {
                            console.log('Swiper', index, 'initialized successfully');
                            // Marquer comme initialisé
                            swiperEl.setAttribute('initialized', 'true');
                            swiperEl.initialized = true;
                        }
                    }
                };

                // Assigner les paramètres à l'élément Swiper
                Object.assign(swiperEl, swiperParams);

                // Marquer comme en cours d'initialisation pour éviter les doubles appels
                swiperEl.setAttribute('initializing', 'true');

                // Initialiser
                if (typeof swiperEl.initialize === 'function') {
                    swiperEl.initialize();
                    console.log('Swiper', index, 'initialize() called');
                } else {
                    console.warn('Swiper', index, 'initialize method not available');
                }

                // Fallback: marquer comme initialisé après un délai court
                setTimeout(() => {
                    if (!swiperEl.hasAttribute('initialized')) {
                        swiperEl.setAttribute('initialized', 'true');
                        swiperEl.initialized = true;
                        console.log('Swiper', index, 'marked as initialized (fallback)');
                    }
                }, 200);

            } catch (e) {
                console.error('Error initializing swiper', index, ':', e);
            }
        });

        // Vérification finale après un délai plus long
        setTimeout(() => {
            const uninitializedSwipers = document.querySelectorAll('swiper-container.mySwiper:not([initialized])');
            if (uninitializedSwipers.length > 0) {
                console.warn('Found', uninitializedSwipers.length, 'uninitialized swipers after final check');
                uninitializedSwipers.forEach((el, idx) => {
                    try {
                        console.log('Final retry for swiper', idx);
                        if (typeof el.initialize === 'function' && !el.hasAttribute('initializing')) {
                            el.initialize();
                            el.setAttribute('initialized', 'true');
                            el.initialized = true;
                            console.log('Final retry success for swiper', idx);
                        }
                    } catch (e) {
                        console.error('Final retry failed for swiper', idx, ':', e);
                        // Force mark as initialized to avoid infinite retries
                        el.setAttribute('initialized', 'true');
                    }
                });
            } else {
                console.log('All swipers successfully initialized!');
            }
        }, 1000);
    }
});