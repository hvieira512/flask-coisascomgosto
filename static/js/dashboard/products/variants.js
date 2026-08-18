import { API, request } from "../../core/api.js";
import { reference } from "./reference.js";

/** The variants panel inside the edit modal: what the product is offered in. */
export async function variantsPanel(product) {
    const { colorSets } = await reference();
    const used = new Set(product.variants.map((v) => v.color_set.id));
    const available = colorSets.filter((cs) => !used.has(cs.id));

    const rows = product.variants.length
        ? product.variants.map((v) => `
            <li class="panel-block px-0 is-gap-1">
              ${window.ColorSet.badge(v.color_set, "mr-auto")}
              <button class="button is-small is-ghost has-text-danger"
                      data-remove-variant="${v.id}" title="Remover">
                <span class="icon"><i class="fa-solid fa-xmark"></i></span>
              </button>
            </li>`).join("")
        : `<li class="has-text-grey is-size-7">Sem cores associadas.</li>`;

    return `
      <ul class="panel is-shadowless mb-3" id="variant-rows">${rows}</ul>
      <div class="field has-addons">
        <div class="control is-expanded">
          <div class="select is-fullwidth is-small">
            <select id="variant-picker"${available.length ? "" : " disabled"}>
              ${available.length
                  ? available.map((cs) => `<option value="${cs.id}">${escapeHtml(cs.name)}</option>`).join("")
                  : `<option>Todos os conjuntos já estão associados</option>`}
            </select>
          </div>
        </div>
        <div class="control">
          <button class="button is-small is-dark" id="add-variant"${available.length ? "" : " disabled"}>
            Adicionar
          </button>
        </div>
      </div>`;
}

export async function addVariant(productId, colorSetId) {
    await request(API.products.variants(productId), {
        method: "POST",
        body: { color_set_id: Number(colorSetId) },
        fallback: "Não foi possível adicionar a cor.",
    });
}

export async function removeVariant(productId, variantId) {
    await request(API.products.variant(productId, variantId), {
        method: "DELETE",
        fallback: "Não foi possível remover a cor.",
    });
}
