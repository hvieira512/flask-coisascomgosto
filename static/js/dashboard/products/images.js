import { API } from "../../core/api.js";
import { escapeHtml } from "./form.js";

/**
 * Every photograph of a product, from both places the API keeps them:
 * `product.images` holds only the product-wide ones, and each variant carries
 * its own. Reading just the first showed nothing for a pinned photograph.
 */
export function allImages(product) {
    const pinned = product.variants.flatMap((variant) =>
        (variant.images ?? []).map((image) => ({ ...image, variant_id: variant.id }))
    );
    return [...(product.images ?? []), ...pinned];
}

/**
 * The photographs panel. An image with no variant is the product-wide fallback;
 * one pinned to a variant shows only for that colour set.
 */
export function imagesPanel(product) {
    const images = allImages(product);

    const rows = images.length
        ? images.map((img) => {
            const variant = product.variants.find((v) => v.id === img.variant_id);
            return `
              <li class="dash-row">
                <img class="dash-thumb" src="${escapeHtml(img.url)}" alt="${escapeHtml(img.alt ?? "")}">
                <span class="is-size-7">
                  ${variant
                      ? window.ColorSet.badge(variant.color_set)
                      : `<span class="tag is-light is-rounded">Todas as cores</span>`}
                </span>
                <button class="button is-small is-ghost has-text-danger"
                        data-remove-image="${img.id}" title="Remover">
                  <span class="icon"><i class="fa-solid fa-xmark"></i></span>
                </button>
              </li>`;
        }).join("")
        : `<li class="has-text-grey is-size-7">Sem fotografias. A loja mostra o marcador de cor.</li>`;

    return `
      <ul class="dash-rows is-flex is-flex-direction-column mb-3" id="image-rows">${rows}</ul>
      <div class="field">
        <div class="file is-small has-name is-fullwidth">
          <label class="file-label">
            <input class="file-input" type="file" id="image-file"
                   accept="image/jpeg,image/png,image/webp">
            <span class="file-cta">
              <span class="file-icon"><i class="fa-solid fa-upload"></i></span>
              <span class="file-label">Escolher fotografia</span>
            </span>
            <span class="file-name" id="image-file-name">Nenhum ficheiro</span>
          </label>
        </div>
        <p class="help">jpg, png ou webp, até 5 MB.</p>
      </div>

      <details class="mb-3">
        <summary class="is-size-7 has-text-grey">Ou indicar um caminho existente</summary>
        <div class="control mt-2">
          <input class="input is-small" id="image-url" placeholder="/static/img/products/nome.jpg">
        </div>
      </details>

      <div class="field has-addons">
        <div class="control is-expanded">
          <div class="select is-fullwidth is-small">
            <select id="image-variant">
              <option value="">Todas as cores (fallback)</option>
              ${product.variants.map((v) =>
                  `<option value="${v.id}">${escapeHtml(v.color_set.name)}</option>`).join("")}
            </select>
          </div>
        </div>
        <div class="control">
          <button class="button is-small is-dark" id="add-image">Adicionar</button>
        </div>
      </div>`;
}

/** Uploads the chosen file and attaches it in one request. */
export async function uploadImage(productId, { file, variantId, alt }) {
    if (!file) throw new Error("Escolha uma fotografia.");

    const body = new FormData();
    body.append("file", file);
    if (variantId) body.append("variant_id", variantId);
    if (alt) body.append("alt", alt);

    // No Content-Type header: the browser sets the multipart boundary.
    const res = await fetch(API.products.uploadImage(productId), {
        method: "POST",
        body,
    });
    if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.message || "Não foi possível carregar a fotografia.");
    }
}

export async function addImage(productId, { url, variantId, alt }) {
    if (!url) throw new Error("Indique o caminho da fotografia.");

    const payload = { url, alt: alt || null };
    if (variantId) payload.variant_id = Number(variantId);

    const res = await fetch(API.products.images(productId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.message || "Não foi possível adicionar a fotografia.");
    }
}

export async function removeImage(productId, imageId) {
    const res = await fetch(
        API.products.image(productId, imageId), { method: "DELETE" }
    );
    if (!res.ok) throw new Error("Não foi possível remover a fotografia.");
}
