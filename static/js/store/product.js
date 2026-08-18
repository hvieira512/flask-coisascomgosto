/**
 * Product detail page.
 *
 * Loads one product, renders its details, and drives the gallery. Selecting a
 * colour shows that colour's photographs, or the placeholder in that colour when
 * there are none of it yet.
 */
(function () {
    const root = document.getElementById("product-detail");
    const errorNotice = document.getElementById("detail-error");
    const productId = root.dataset.productId;

    // The gallery needs the product so it can draw the type/colour
    // placeholder when there are no photographs.
    let gallery;

    /**
     * A selected colour shows only its own photographs — never the product-level
     * ones. Falling back to those made three of a piece's four colours show the
     * same picture, so clicking a swatch looked broken rather than empty. With no
     * colours at all, the product-level photographs are what there is.
     */
    function imagesFor(product, variant) {
        if (variant) return variant.images || [];
        return product.images || [];
    }

    /** The specification list: the facts a buyer asks about. */
    function renderMeta(product) {
        const meta = document.getElementById("product-meta");
        const rows = [];

        if (product.material) rows.push(["Material", product.material.name]);
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
                <button class="button is-small" type="button"
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
                option.classList.remove("is-dark");
                option.setAttribute("aria-pressed", "false");
            });
            if (!already) {
                button.classList.add("is-dark");
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
                return `
                  <button class="tag is-rounded color-set-badge variant-option${position === activeIndex ? " is-active" : ""}"
                          type="button" data-variant-index="${position}"
                          style="${window.ColorSet.style(variant.color_set)}">
                    ${window.ColorSet.dots(variant.color_set)}<span class="color-set-name">${escapeHtml(variant.color_set.name)}</span>
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
            chosen.colorSet = variant.color_set.name;
            renderEnquiry(product);
            gallery.render(imagesFor(product, variant), variant);
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
