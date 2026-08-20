/**
 * Product detail page.
 *
 * Loads one product, renders its details, and drives the gallery. Selecting a
 * colour shows that colour's photographs, or the placeholder in that colour when
 * there are none of it yet.
 */

import { API, request } from "../core/api.js";
import { ColorSet } from "./color-set.js";
import { StoreGallery } from "./gallery.js";
import { escapeHtml } from "../core/html.js";

(function () {
    const root = document.getElementById("product-detail");
    const errorNotice = document.getElementById("detail-error");
    const productId = root.dataset.productId;

    // The gallery needs the product so it can draw the type/colour
    // placeholder when there are no photographs.
    let gallery;

    /**
     * The chosen colour's photographs first, then the piece's own, each tagged with
     * the group the strip labels it under.
     *
     * A colour used to show only its own, on the grounds that falling back to the
     * piece's made three of four colours show the same picture and clicking a swatch
     * look broken. That reasoning was about an unlabelled fallback: the piece's
     * photographs are now a labelled group of their own, and the stage says
     * "Fotografia da peça" when it is showing one — so they are reachable instead of
     * invisible, which is what most of the catalogue's photographs were.
     */
    /**
     * The chosen colour's photographs, then the piece's own.
     *
     * Deliberately not the other colours': a colour's photographs appear by choosing
     * that colour, and nothing else. Offering them all made the gallery a tour of the
     * whole piece, which is not what a shopper looking at one colour asked for.
     */
    function imagesFor(product, variant) {
        const tag = (list, group) => (list || []).map((image) => ({ ...image, group }));

        if (!variant) return tag(product.images, "piece");
        return [...tag(variant.images, "colour"), ...tag(product.images, "piece")];
    }

    /** The specification list: the facts a buyer asks about. */
    function renderMeta(product) {
        const meta = document.getElementById("product-meta");
        const rows = [];

        if (product.material) rows.push(["Material", product.material.name]);
        if (product.type) rows.push(["Tipo", product.type.name]);
        if (product.collection) rows.push(["Colecção", product.collection.name]);
        if (product.default_size) rows.push(["Tamanho base", product.default_size.name]);

        meta.innerHTML = rows
            .map(
                ([label, value]) => `
                <div class="spec-row">
                  <dt>${escapeHtml(label)}</dt>
                  <dd>${escapeHtml(value)}</dd>
                </div>`
            )
            .join("");
    }

    // What the visitor has picked, folded into the enquiry they send. There is no
    // basket, so a chosen colour and size have nowhere else to go — and a control
    // that looks pressable has to do something.
    let chosen = { colorSet: null, size: null };

    /** Pre-fill the WhatsApp message with the piece, colour and size on screen. */
    function renderEnquiry(product) {
        const link = document.getElementById("enquiry-link");
        if (!link) return;

        const parts = [`Olá! Gostaria de saber mais sobre "${product.name}"`];
        if (chosen.colorSet) parts.push(`em ${chosen.colorSet}`);
        if (chosen.size) parts.push(`tamanho ${chosen.size}`);

        const base = link.getAttribute("href").split("?")[0];
        link.href = `${base}?text=${encodeURIComponent(`${parts.join(", ")}.`)}`;
    }

    function renderSizes(product) {
        const block = document.getElementById("sizes-block");
        const options = document.getElementById("size-options");

        if (!product.sizes || product.sizes.length === 0) {
            block.hidden = true;
            return;
        }

        block.hidden = false;
        options.innerHTML = product.sizes
            .map((size) => `
                <button class="btn btn-light" type="button"
                        data-size="${escapeHtml(size.name)}"
                        aria-pressed="false">${escapeHtml(size.name)}</button>`)
            .join("");

        options.addEventListener("click", (event) => {
            const button = event.target.closest("[data-size]");
            if (!button) return;

            // Clicking the chosen size again clears it, so a visitor who only
            // wanted to look is not stuck having asked for a size.
            const already = button.getAttribute("aria-pressed") === "true";
            options.querySelectorAll("[data-size]").forEach((option) => {
                option.classList.remove("btn-dark");
                option.classList.add("btn-light");
                option.setAttribute("aria-pressed", "false");
            });
            if (!already) {
                button.classList.remove("btn-light");
                button.classList.add("btn-dark");
                button.setAttribute("aria-pressed", "true");
            }

            chosen.size = already ? null : button.dataset.size;
            renderEnquiry(product);
        });
    }

    function renderVariants(product, activeIndex) {
        const block = document.getElementById("variants-block");
        const options = document.getElementById("variant-options");

        if (!product.variants || product.variants.length === 0) {
            block.hidden = true;
            return;
        }

        block.hidden = false;
        options.innerHTML = product.variants
            .map((variant, position) => {
                const chosen = position === activeIndex;
                return `
                  <div class="col">
                    <button class="color-set-badge variant-option${chosen ? " is-active" : ""}"
                            type="button" data-variant-index="${position}"
                            aria-pressed="${chosen}"
                            style="${ColorSet.style(variant.color_set)}">
                      ${ColorSet.dots(variant.color_set)}<span class="color-set-name">${escapeHtml(variant.color_set.name)}</span><span class="variant-check" aria-hidden="true"><i class="fa-solid fa-check"></i></span>
                    </button>
                  </div>`;
            })
            .join("");

        options.addEventListener("click", (event) => {
            const button = event.target.closest("[data-variant-index]");
            if (button) selectVariant(product, Number(button.dataset.variantIndex));
        });
    }

    /** Choose a colour: mark its swatch, tell the enquiry, and hand the gallery that
     *  colour's photographs. */
    function selectVariant(product, index) {
        const variant = product.variants?.[index];
        if (!variant) return;

        document.querySelectorAll("#variant-options .variant-option").forEach((option) => {
            const isChosen = Number(option.dataset.variantIndex) === index;
            option.classList.toggle("is-active", isChosen);
            option.setAttribute("aria-pressed", String(isChosen));
        });

        chosen.colorSet = variant.color_set.name;
        renderEnquiry(product);
        gallery.render(imagesFor(product, variant), variant);
    }

    (async function init() {
        let product;
        try {
            product = await request(API.products.get(productId));
        } catch (error) {
            root.hidden = true;
            errorNotice.hidden = false;
            return;
        }

        document.title = `${product.name} · Coisas com Gosto`;
        document.getElementById("crumb-name").textContent = product.name;
        document.getElementById("product-name").textContent = product.name;
        document.getElementById("product-description").textContent = product.description || "";

        gallery = StoreGallery.create(root, product);

        // Open on the first colour that has been photographed, rather than
        // simply the first: a piece whose opening colour has no photograph yet
        // would otherwise greet every visitor with the placeholder while a real
        // photograph of it sat one swatch away.
        const variants = product.variants || [];
        const photographed = variants.findIndex((v) => v.images?.length);
        const activeIndex = photographed === -1 ? 0 : photographed;

        chosen.colorSet = variants[activeIndex]?.color_set?.name ?? null;

        renderMeta(product);
        renderVariants(product, activeIndex);
        renderSizes(product);
        renderEnquiry(product);

        gallery.render(imagesFor(product, variants[activeIndex]), variants[activeIndex]);
    })();
})();
