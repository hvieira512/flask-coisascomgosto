/**
 * Product detail page.
 *
 * Loads one product, renders its details, and drives the gallery. Selecting a
 * colour variant swaps the gallery to that variant's photos, falling back to
 * the product-level images when the variant has none of its own.
 */
(function () {
    const root = document.getElementById("product-detail");
    const errorNotice = document.getElementById("detail-error");
    const productId = root.dataset.productId;

    // The gallery needs the product so it can draw the type/colour
    // placeholder when there are no photographs.
    let gallery;

    function imagesFor(product, variant) {
        if (variant && variant.images && variant.images.length > 0) {
            return variant.images;
        }
        return product.images || [];
    }

    /** The specification list: the facts a buyer asks about. */
    function renderMeta(product) {
        const meta = document.getElementById("product-meta");
        const rows = [];

        if (product.category) rows.push(["Categoria", product.category.name]);
        if (product.type) {
            const name = product.type.parent
                ? `${product.type.parent.name} · ${product.type.name}`
                : product.type.name;
            rows.push(["Tipo", name]);
        }
        if (product.collection) rows.push(["Colecção", product.collection.name]);
        if (product.default_size) rows.push(["Tamanho base", product.default_size.name]);
        if (product.variants?.length) {
            rows.push(["Cores disponíveis", String(product.variants.length)]);
        }

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

    /** Pre-fill the WhatsApp message with the piece the visitor is looking at. */
    function renderEnquiry(product) {
        const link = document.getElementById("enquiry-link");
        if (!link) return;

        const base = link.getAttribute("href").split("?")[0];
        const message = `Olá! Gostaria de saber mais sobre "${product.name}".`;
        link.href = `${base}?text=${encodeURIComponent(message)}`;
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
            .map((size) => `<button class="button is-small" type="button">${escapeHtml(size.name)}</button>`)
            .join("");
    }

    function renderVariants(product) {
        const block = document.getElementById("variants-block");
        const options = document.getElementById("variant-options");

        if (!product.variants || product.variants.length === 0) {
            block.hidden = true;
            return;
        }

        block.hidden = false;
        options.innerHTML = product.variants
            .map((variant, position) => {
                const colors = variant.color_set.colors || [];
                const swatch =
                    colors.length > 1
                        ? `<span class="swatch-pair" style="background:linear-gradient(135deg,
                             ${escapeHtml(colors[0].hex || "#ddd")} 0 50%,
                             ${escapeHtml(colors[1].hex || "#bbb")} 50% 100%)"></span>`
                        : `<span class="swatch"
                             style="background:${escapeHtml(colors[0]?.hex || "#ddd")}"></span>`;

                return `
                  <button class="variant-option${position === 0 ? " is-active" : ""}"
                          type="button" data-variant-index="${position}">
                    ${swatch}${escapeHtml(variant.color_set.name)}
                  </button>`;
            })
            .join("");

        options.addEventListener("click", (event) => {
            const button = event.target.closest("[data-variant-index]");
            if (!button) return;

            options.querySelectorAll(".variant-option").forEach((option) =>
                option.classList.toggle("is-active", option === button)
            );

            const variant = product.variants[Number(button.dataset.variantIndex)];
            gallery.render(imagesFor(product, variant));
        });
    }

    (async function init() {
        let product;
        try {
            product = await StoreApi.product(productId);
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

        renderMeta(product);
        renderVariants(product);
        renderSizes(product);
        renderEnquiry(product);

        // Open on the first variant's photos when there are any, so the page
        // matches the pre-selected colour swatch.
        const firstVariant = (product.variants || [])[0];
        gallery.render(imagesFor(product, firstVariant));
    })();
})();
