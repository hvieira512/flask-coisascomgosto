import { API, request } from "../../core/api.js";
import { ColorSet } from "../../store/color-set.js";
import { escapeHtml } from "../../core/html.js";

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
 * The photographs panel. Every photograph belongs to one of the piece's colours: a
 * photograph of a piece is a photograph of it in a colour, so there is no product-wide
 * one to add. The rows can still show photographs that have none — the seeded ones do
 * — and those read as something to deal with.
 */
export function imagesPanel(product) {
    const images = allImages(product);

    const rows = images.length
        ? images.map((img) => {
            const variant = product.variants.find((v) => v.id === img.variant_id);
            return `
              <li class="panel-block px-0 is-gap-1">
                <img class="dash-thumb" src="${escapeHtml(img.url)}" alt="${escapeHtml(img.alt ?? "")}">
                <span class="is-size-7 mr-auto">
                  ${variant
                      ? ColorSet.badge(variant.color_set)
                      // Cannot be made any more; the ones that exist predate that and
                      // each needs pointing at a colour, so it reads as a job to do
                      // rather than as a choice that was available.
                      : `<span class="tag is-rounded chip is-attention"
                               title="Esta fotografia não está associada a nenhuma cor">
                           Sem cor
                         </span>`}
                </span>
                <button class="button is-small is-ghost has-text-danger"
                        data-remove-image="${img.id}" title="Remover">
                  <span class="icon"><i class="fa-solid fa-xmark"></i></span>
                </button>
              </li>`;
        }).join("")
        : `<li class="has-text-grey is-size-7">Sem fotografias. A loja mostra o marcador de cor.</li>`;

    return `
      <ul class="panel is-shadowless mb-3" id="image-rows">${rows}</ul>
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
            <select id="image-variant"${product.variants.length ? "" : " disabled"}>
              ${product.variants.length
                  ? product.variants.map((v) =>
                        `<option value="${v.id}">${escapeHtml(v.color_set.name)}</option>`).join("")
                  : `<option value="">Nenhuma cor associada</option>`}
            </select>
          </div>
        </div>
        <div class="control">
          <button class="button is-small is-dark" id="add-image"${
              product.variants.length ? "" : " disabled"}>Adicionar</button>
        </div>
      </div>

      ${product.variants.length
          ? `<p class="help">Cada fotografia é de uma cor. Escolha qual.</p>`
          : `<p class="help has-text-weight-medium">
               Associe primeiro uma cor à peça, no separador Cores: uma fotografia é
               sempre de uma cor.
             </p>`}`;
}

/**
 * Uploads the chosen file and attaches it in one request.
 *
 * A colour is required. The API still accepts a photograph without one — which is how
 * the seeded photographs came to have none — but nothing here creates another.
 */
export async function uploadImage(productId, { file, variantId, alt }) {
    if (!file) throw new Error("Escolha uma fotografia.");
    if (!variantId) throw new Error("Escolha a cor a que a fotografia pertence.");

    const body = new FormData();
    body.append("file", file);
    body.append("variant_id", variantId);
    if (alt) body.append("alt", alt);

    await request(API.products.uploadImage(productId), {
        method: "POST",
        body,
        fallback: "Não foi possível carregar a fotografia.",
    });
}

export async function addImage(productId, { url, variantId, alt }) {
    if (!url) throw new Error("Indique o caminho da fotografia.");
    if (!variantId) throw new Error("Escolha a cor a que a fotografia pertence.");

    const payload = { url, alt: alt || null, variant_id: Number(variantId) };

    await request(API.products.images(productId), {
        method: "POST",
        body: payload,
        fallback: "Não foi possível adicionar a fotografia.",
    });
}

export async function removeImage(productId, imageId) {
    await request(API.products.image(productId, imageId), {
        method: "DELETE",
        fallback: "Não foi possível remover a fotografia.",
    });
}
