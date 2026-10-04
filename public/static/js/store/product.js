import { API, request } from "../core/api.js";
import { ColorSet } from "./color-set.js";
import { StoreGallery } from "./gallery.js";
import { Track } from "./track.js";
import { escapeHtml } from "../core/html.js";

(function () {
    const root = document.getElementById("product-detail");
    const errorNotice = document.getElementById("detail-error");
    const productId = root.dataset.productId;

    let gallery;

    function imagesFor(product, variant) {
        return variant ? variant.images || [] : [];
    }

    // "Madeira e pasta de modelar", and with three "a, b e c" — a string of
    // "e"s reads as a list nobody finished writing.
    const list = (names) => names.length > 2
        ? `${names.slice(0, -1).join(", ")} e ${names.at(-1)}`
        : names.join(" e ");

    function renderMeta(product) {
        const meta = document.getElementById("product-meta");
        const rows = [];

        const materials = (product.materials ?? []).map((m) => m.name);
        if (materials.length) {
            rows.push([
                materials.length === 1 ? "Material" : "Materiais",
                list(materials),
            ]);
        }
        if (product.type) rows.push(["Tipo", product.type.name]);
        const collections = (product.collections ?? []).map((c) => c.name);
        if (collections.length) {
            rows.push([
                collections.length === 1 ? "Colecção" : "Colecções",
                list(collections),
            ]);
        }
        if (product.default_size) rows.push(["Tamanho base", product.default_size.name]);

        meta.innerHTML = rows
            .map(
                ([label, value]) => `
                <div class="spec-row">
                  <dt>${escapeHtml(label)}</dt>
                  <dd class="mb-0">${escapeHtml(value)}</dd>
                </div>`
            )
            .join("");
    }

    let chosen = { variant: null, size: null };

    function renderEnquiry(product) {
        const link = document.getElementById("enquiry-link");
        if (!link) return;

        const parts = [`Olá! Gostaria de saber mais sobre "${product.name}"`];
        if (chosen.variant) parts.push(`em ${chosen.variant.color_set.name}`);
        if (chosen.size) parts.push(`tamanho ${chosen.size.name}`);

        const base = link.getAttribute("href").split("?")[0];
        link.href = `${base}?text=${encodeURIComponent(`${parts.join(", ")}.`)}`;
    }

    function wireEnquiryTracking(product) {
        const link = document.getElementById("enquiry-link");
        if (!link) return;

        link.addEventListener("click", () => {
            Track.enquiry({
                productId: product.id,
                variantId: chosen.variant?.id ?? null,
                sizeId: chosen.size?.id ?? null,
            });
        });
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

            chosen.size = already
                ? null
                : product.sizes.find((s) => s.name === button.dataset.size) ?? null;
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
            .map((variant, position) => `
              <button class="variant-option" type="button"
                      data-variant-index="${position}"
                      aria-pressed="${position === activeIndex}"
                      title="${escapeHtml(variant.color_set?.name ?? "")}">
                ${ColorSet.dots(variant.color_set)}
              </button>`)
            .join("");
        nameChosen(product, activeIndex);

        options.addEventListener("click", (event) => {
            const button = event.target.closest("[data-variant-index]");
            if (button) selectVariant(product, Number(button.dataset.variantIndex));
        });
    }

    function nameChosen(product, index) {
        const target = document.getElementById("variant-chosen");
        if (target) target.textContent = product.variants?.[index]?.color_set?.name ?? "";
    }

    function selectVariant(product, index) {
        const variant = product.variants?.[index];
        if (!variant) return;

        document.querySelectorAll("#variant-options [data-variant-index]").forEach((option) => {
            const isChosen = Number(option.dataset.variantIndex) === index;
            option.setAttribute("aria-pressed", String(isChosen));
        });
        nameChosen(product, index);

        chosen.variant = variant;
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
        const description = document.getElementById("product-description");
        description.textContent = product.description || "";
        description.hidden = !product.description;

        gallery = StoreGallery.create(root, product);

        const variants = product.variants || [];
        const photographed = variants.findIndex((v) => v.images?.length);
        const activeIndex = photographed === -1 ? 0 : photographed;

        chosen.variant = variants[activeIndex] ?? null;

        Track.view(product.id);
        wireEnquiryTracking(product);

        renderMeta(product);
        renderVariants(product, activeIndex);
        renderSizes(product);
        renderEnquiry(product);

        gallery.render(imagesFor(product, variants[activeIndex]), variants[activeIndex]);
    })();
})();
