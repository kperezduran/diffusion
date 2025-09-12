/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';
import {renderToElement} from "@web/core/utils/render";

publicWidget.registry.BookSliderLoader = publicWidget.Widget.extend({
    selector: '.js_loadslider_books',

    init() {
        this._super(...arguments);
        this.rpc = this.bindService('rpc');
        this.orm = this.bindService('orm');
        this._sliders = [];
    },

    start: async function () {
        await this._super(...arguments);
        try {
            const container = this.el;
            const onlyId = container?.dataset?.sliderId ? parseInt(container.dataset.sliderId) : null;
            let sliders = [];

            if (onlyId) {
                sliders = [{
                    id: onlyId,
                    title: container.dataset.title || '',
                    name: container.dataset.name || '',
                    website_sequence: 0
                }];
            } else {
                sliders = await this.rpc('/slider/published');
            }

            if (!Array.isArray(sliders)) sliders = [];

            for (const s of sliders) {
                await this._mountSliderBlock(s);
            }
        } catch (err) {
            console.warn('BookSliderLoader init failed', err);
        }
    },

    _mountSliderBlock: async function (slider) {
        const container = this.el;
        const title = slider.title || slider.name || '';

        // Rendre le carousel Bootstrap
        const blockEl = renderToElement('net_diffusion_fel.slider_ajax', {
            slider_id: slider.id,
            title,
        });
        container.appendChild(blockEl);

        // Références DOM
        const carouselInner = blockEl.querySelector('.netfel-carousel-inner');
        const carouselIndicators = blockEl.querySelector('.netfel-carousel-indicators');
        const loader = blockEl.querySelector('.netfel-slider-loader');
        const carouselEl = blockEl.querySelector('.netfel-carousel');

        // État du slider
        const state = {
            id: slider.id,
            total: 0,
            loaded: 0,
            currentSlide: 0,
            itemsPerSlide: 5, // 5 produits par slide
            carouselInner,
            carouselIndicators,
            loader,
            carouselEl,
            blockEl,
        };
        this._sliders.push(state);

        // Chargement initial
        await this._loadInitialProducts(state);

        // Initialiser les événements
        this._setupCarouselEvents(state);
    },

    _loadInitialProducts: async function(state) {
        try {
            // Charger les premiers produits (2 slides de 5 produits)
            const initialLoad = state.itemsPerSlide * 2;
            const resp = await this.rpc('/slider/products', {
                slider_id: state.id,
                limit: initialLoad,
                offset: 0,
            });

            if (!resp || !Array.isArray(resp.products)) return;

            state.total = resp.total || 0;
            const products = resp.products;

            // Grouper les produits par slides
            this._createSlides(state, products, true);

            // Masquer le loader
            if (state.loader) {
                state.loader.style.display = 'none';
            }

            state.loaded = products.length;

        } catch (error) {
            console.warn('Erreur lors du chargement initial', error);
            if (state.loader) {
                state.loader.innerHTML = '<div class="text-danger">Erreur de chargement</div>';
            }
        }
    },

    _createSlides: function(state, products, isInitial = false) {
        const itemsPerSlide = state.itemsPerSlide;
        const slides = [];

        // Grouper les produits par slides de 5
        for (let i = 0; i < products.length; i += itemsPerSlide) {
            const slideProducts = products.slice(i, i + itemsPerSlide);
            slides.push(slideProducts);
        }

        // Créer les éléments de slide
        slides.forEach((slideProducts, index) => {
            const isActive = isInitial && index === 0;
            const slideEl = renderToElement('net_diffusion_fel.carousel_slide', {
                products: slideProducts,
                isActive: isActive,
            });

            state.carouselInner.appendChild(slideEl);

            // Ajouter l'indicateur
            if (state.carouselIndicators) {
                const indicator = document.createElement('button');
                indicator.type = 'button';
                indicator.setAttribute('data-bs-target', `#productCarousel${state.id}`);
                indicator.setAttribute('data-bs-slide-to', state.currentSlide);
                indicator.setAttribute('aria-label', `Slide ${state.currentSlide + 1}`);
                if (isActive) {
                    indicator.classList.add('active');
                    indicator.setAttribute('aria-current', 'true');
                }
                state.carouselIndicators.appendChild(indicator);
            }

            state.currentSlide++;
        });
    },

    _setupCarouselEvents: function(state) {
        const nextBtn = state.blockEl.querySelector('.netfel-carousel-next');

        if (nextBtn) {
            nextBtn.addEventListener('click', async (e) => {
                // Vérifier si on doit charger plus de produits
                const currentActiveIndex = this._getCurrentSlideIndex(state);
                const totalSlides = state.carouselInner.children.length;

                // Si on est sur l'avant-dernière slide et qu'il y a plus de produits à charger
                if (currentActiveIndex >= totalSlides - 2 && state.loaded < state.total) {
                    await this._loadMoreProducts(state);
                }
            });
        }

        // Événement de changement de slide Bootstrap
        state.carouselEl.addEventListener('slid.bs.carousel', (e) => {
            const currentIndex = Array.from(e.target.querySelectorAll('.carousel-item')).indexOf(e.relatedTarget);
            const totalSlides = state.carouselInner.children.length;

            // Pré-charger si on approche de la fin
            if (currentIndex >= totalSlides - 2 && state.loaded < state.total) {
                this._loadMoreProducts(state);
            }
        });
    },

    _getCurrentSlideIndex: function(state) {
        const activeSlide = state.carouselInner.querySelector('.carousel-item.active');
        return Array.from(state.carouselInner.children).indexOf(activeSlide);
    },

    _loadMoreProducts: async function(state) {
        try {
            const resp = await this.rpc('/slider/products', {
                slider_id: state.id,
                limit: state.itemsPerSlide,
                offset: state.loaded,
            });

            if (!resp || !Array.isArray(resp.products) || resp.products.length === 0) return;

            // Créer une nouvelle slide avec les nouveaux produits
            this._createSlides(state, resp.products, false);

            state.loaded += resp.products.length;

        } catch (error) {
            console.warn('Erreur lors du chargement supplémentaire', error);
        }
    },
});