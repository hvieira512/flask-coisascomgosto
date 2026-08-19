import { API, request } from "../../core/api.js";
import { ColorSet } from "../../store/color-set.js";
import { escapeHtml } from "../../core/html.js";
import { reference } from "./reference.js";

/**
 * The create wizard's colour step: which colour sets the piece will be offered in,
 * chosen before the piece exists.
 *
 * A variant needs a product id, so nothing here can be written while the wizard is
 * open. The choice is held in the DOM and posted once the product has been created,
 * which keeps the wizard's promise that a half-answered form leaves nothing behind.
 *
 * Toggle chips rather than the edit panel's picker-and-Adicionar: that panel writes
 * on every click, which is right when the piece exists and impossible here.
 */
export function variantChoiceStep(colorSets) {
    if (!colorSets.length) {
        return `
          <div data-step="variants">
            <p class="has-text-grey is-size-7">
              Ainda não há conjuntos de cores. Crie-os em Cores e depois associe-os
              a esta peça.
            </p>
          </div>`;
    }

    return `
      <div data-step="variants">
        <div class="tags" id="variant-choices">
          ${colorSets.map((set) => `
            <button type="button" class="variant-choice" data-color-set-id="${set.id}"
                    aria-pressed="false">${ColorSet.badge(set)}</button>`).join("")}
        </div>
        <p class="help">
          Em que cores a peça se faz. Opcional — pode associá-las mais tarde, e as
          fotografias de cada cor entram no passo seguinte.
        </p>
      </div>`;
}

/** Wires the chips and returns a reader for what is chosen. */
export function wireVariantChoice(root) {
    const choices = root.querySelector("#variant-choices");
    if (!choices) return () => [];

    choices.addEventListener("click", (event) => {
        const chip = event.target.closest(".variant-choice");
        if (!chip) return;

        const on = chip.getAttribute("aria-pressed") === "true";
        chip.setAttribute("aria-pressed", String(!on));
        chip.classList.toggle("is-active", !on);
    });

    return () =>
        [...choices.querySelectorAll('.variant-choice[aria-pressed="true"]')]
            .map((chip) => Number(chip.dataset.colorSetId));
}

/** The variants panel inside the edit modal: what the product is offered in. */
export async function variantsPanel(product) {
    const { colorSets } = await reference();
    const used = new Set(product.variants.map((v) => v.color_set.id));
    const available = colorSets.filter((cs) => !used.has(cs.id));

    const rows = product.variants.length
        ? product.variants.map((v) => `
            <li class="panel-block px-0 is-gap-1">
              ${ColorSet.badge(v.color_set, "mr-auto")}
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

/**
 * Attach several colour sets to a piece that has just been created.
 *
 * A 409 means that colour is already attached, which is not a failure here: the
 * product is created before its variants, so a wizard whose first attempt failed
 * halfway is retried against a product that already has some of them.
 */
export async function addVariants(productId, colorSetIds) {
    for (const colorSetId of colorSetIds) {
        try {
            await addVariant(productId, colorSetId);
        } catch (error) {
            if (error.status !== 409) throw error;
        }
    }
}

export async function removeVariant(productId, variantId) {
    await request(API.products.variant(productId, variantId), {
        method: "DELETE",
        fallback: "Não foi possível remover a cor.",
    });
}
