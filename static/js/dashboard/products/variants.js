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
        <p class="help mb-4">
          Em que cores a peça se faz. Opcional — pode associá-las mais tarde.
        </p>

        <!-- Only the chosen colours are asked for a photograph, so the dialog grows
             with the answer rather than with the list. -->
        <div id="variant-photos" hidden>
          <label class="label is-small">Fotografias destas cores</label>
          <ul class="panel is-shadowless mb-2" id="variant-photo-rows"></ul>
          <p class="help">
            Uma por cor, se já as tirou. As restantes entram no passo seguinte.
          </p>
        </div>
      </div>`;
}

/**
 * Wires the chips and their photo slots, and returns a reader for both.
 *
 * The files live in a Map rather than in the inputs: the rows are re-rendered every
 * time a chip is toggled, and re-rendering an <input type="file"> empties it — a
 * photograph chosen for the first colour would vanish when the second was ticked.
 */
export function wireVariantChoice(root) {
    const choices = root.querySelector("#variant-choices");
    if (!choices) return () => [];

    const photos = new Map();
    const panel = root.querySelector("#variant-photos");
    const rows = root.querySelector("#variant-photo-rows");

    const chosen = () =>
        [...choices.querySelectorAll('.variant-choice[aria-pressed="true"]')]
            .map((chip) => Number(chip.dataset.colorSetId));

    const nameOf = (id) =>
        choices.querySelector(`[data-color-set-id="${id}"]`).textContent.trim();

    const badgeOf = (id) =>
        choices.querySelector(`[data-color-set-id="${id}"]`).innerHTML;

    function drawRows() {
        const ids = chosen();
        panel.hidden = ids.length === 0;
        // A colour that has been unticked takes its photograph with it, or the
        // upload would arrive for a variant the piece does not have.
        [...photos.keys()].forEach((id) => {
            if (!ids.includes(id)) photos.delete(id);
        });

        rows.innerHTML = ids.map((id) => {
            const file = photos.get(id);
            return `
              <li class="panel-block px-0 is-justify-content-space-between"
                  data-photo-for="${id}">
                <span class="is-flex is-align-items-center is-gap-1">${badgeOf(id)}</span>
                <span class="is-flex is-align-items-center is-gap-1">
                  ${file
                      ? `<span class="is-size-7 has-text-grey">${escapeHtml(file.name)}</span>
                         <button type="button" class="button is-small is-ghost has-text-danger"
                                 data-photo-clear aria-label="Remover a fotografia de ${escapeHtml(nameOf(id))}">
                           <span class="icon"><i class="fa-solid fa-xmark"></i></span>
                         </button>`
                      : `<div class="file is-small">
                           <label class="file-label">
                             <input class="file-input" type="file" data-photo-input
                                    accept="image/jpeg,image/png,image/webp"
                                    aria-label="Fotografia de ${escapeHtml(nameOf(id))}">
                             <span class="file-cta">
                               <span class="file-icon"><i class="fa-solid fa-image"></i></span>
                               <span class="file-label">Escolher…</span>
                             </span>
                           </label>
                         </div>`}
                </span>
              </li>`;
        }).join("");
    }

    choices.addEventListener("click", (event) => {
        const chip = event.target.closest(".variant-choice");
        if (!chip) return;

        const on = chip.getAttribute("aria-pressed") === "true";
        chip.setAttribute("aria-pressed", String(!on));
        chip.classList.toggle("is-active", !on);
        drawRows();
    });

    // Delegated because the rows are rebuilt on every toggle. `change` bubbles.
    rows.addEventListener("change", (event) => {
        const input = event.target.closest("[data-photo-input]");
        if (!input) return;

        const id = Number(input.closest("[data-photo-for]").dataset.photoFor);
        const file = input.files[0];
        if (file) photos.set(id, file);
        drawRows();
    });

    rows.addEventListener("click", (event) => {
        const clear = event.target.closest("[data-photo-clear]");
        if (!clear) return;

        photos.delete(Number(clear.closest("[data-photo-for]").dataset.photoFor));
        drawRows();
    });

    return () => chosen().map((id) => ({ colorSetId: id, file: photos.get(id) ?? null }));
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
