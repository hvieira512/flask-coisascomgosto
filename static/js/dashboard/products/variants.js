import { API } from "../../core/api.js";
import { reference } from "./reference.js";

/** The variants panel inside the edit modal: what the product is offered in. */
export async function variantsPanel(product) {
    const { colorSets } = await reference();
    const used = new Set(product.variants.map((v) => v.color_set.id));
    const available = colorSets.filter((cs) => !used.has(cs.id));

    const rows = product.variants.length
        ? product.variants.map((v) => `
            <li class="dash-row">
              ${window.ColorSet.badge(v.color_set)}
              <button class="button is-small is-ghost has-text-danger"
                      data-remove-variant="${v.id}" title="Remover">
                <span class="icon"><i class="fa-solid fa-xmark"></i></span>
              </button>
            </li>`).join("")
        : `<li class="has-text-grey is-size-7">Sem cores associadas.</li>`;

    return `
      <ul class="dash-rows is-flex is-flex-direction-column mb-3" id="variant-rows">${rows}</ul>
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
    const res = await fetch(API.products.variants(productId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ color_set_id: Number(colorSetId) }),
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.message || "Não foi possível adicionar a cor.");
    }
}

export async function removeVariant(productId, variantId) {
    const res = await fetch(
        API.products.variant(productId, variantId), { method: "DELETE" }
    );
    if (!res.ok) throw new Error("Não foi possível remover a cor.");
}
