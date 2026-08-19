import { API, request } from "../../core/api.js";
import { ColorSet } from "../../store/color-set.js";
import { PhotoPicker } from "../../core/photo-picker.js";
import { escapeHtml, fieldIcon } from "../../core/html.js";
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
            <p class="text-body-secondary fs-7">
              Ainda não há conjuntos de cores. Crie-os em Cores e depois associe-os
              a esta peça.
            </p>
          </div>`;
    }

    return `
      <div data-step="variants">
        <div class="d-flex flex-wrap gap-1" id="variant-choices">
          ${colorSets.map((set) => `
            <button type="button" class="variant-choice" data-color-set-id="${set.id}"
                    aria-pressed="false">${ColorSet.badge(set)}</button>`).join("")}
        </div>
        <p class="help mt-2 mb-3">
          Em que cores a peça se faz. Opcional — pode associá-las mais tarde.
        </p>

        <!-- Only the chosen colours are asked for a photograph, so the dialog grows
             with the answer rather than with the list. -->
        <div id="variant-photos" hidden>
          <label class="form-label fs-7">Fotografias destas cores</label>
          <ul class="list-group list-group-flush mb-2" id="variant-photo-rows"></ul>
          <p class="help">
            Quantas quiser por cor, se já as tirou. As restantes podem entrar depois,
            no separador Fotografias.
          </p>
        </div>
      </div>`;
}

/**
 * Wires the chips and a photo tray for each colour chosen, and returns a reader for
 * both.
 *
 * Each colour gets its own tray because a variant may be photographed more than
 * once. The trays are kept in a Map and moved in and out of the DOM rather than
 * rebuilt, so a photograph chosen for the first colour survives a second being
 * ticked — a redrawn tray would lose the files it was holding.
 */
export function wireVariantChoice(root) {
    const choices = root.querySelector("#variant-choices");
    if (!choices) return () => [];

    const trays = new Map();
    const panel = root.querySelector("#variant-photos");
    const rows = root.querySelector("#variant-photo-rows");

    const chosen = () =>
        [...choices.querySelectorAll('.variant-choice[aria-pressed="true"]')]
            .map((chip) => Number(chip.dataset.colorSetId));

    const chipOf = (id) => choices.querySelector(`[data-color-set-id="${id}"]`);

    /** One row per chosen colour: its badge, and a tray under it. */
    function rowFor(id) {
        if (trays.has(id)) return trays.get(id).row;

        const row = document.createElement("li");
        row.className = "list-group-item px-0 d-flex flex-column align-items-stretch";
        row.dataset.photoFor = String(id);
        row.innerHTML = `
            <span class="d-flex align-items-center gap-1 mb-2">${chipOf(id).innerHTML}</span>
            <div data-photo-tray></div>`;

        const tray = PhotoPicker.mount(row.querySelector("[data-photo-tray]"), {
            multiple: true,
            hint: "Arraste, escolha ou tire",
        });
        trays.set(id, { row, tray });
        return row;
    }

    function drawRows() {
        const ids = chosen();
        panel.hidden = ids.length === 0;

        // A colour that has been unticked takes its photographs with it, or the
        // upload would arrive for a variant the piece does not have. The row has to
        // be taken out of the list by hand: nothing here rebuilds the list, so
        // forgetting the tray alone left the row on screen.
        [...trays.keys()].forEach((id) => {
            if (ids.includes(id)) return;
            trays.get(id).row.remove();
            trays.delete(id);
        });

        // Appending an element that is already in the list moves it, so the rows
        // end up in the chips' order without any of them being re-created.
        ids.forEach((id) => rows.appendChild(rowFor(id)));
    }

    choices.addEventListener("click", (event) => {
        const chip = event.target.closest(".variant-choice");
        if (!chip) return;

        const on = chip.getAttribute("aria-pressed") === "true";
        chip.setAttribute("aria-pressed", String(!on));
        chip.classList.toggle("is-active", !on);
        drawRows();
    });

    return () =>
        chosen().map((id) => ({
            colorSetId: id,
            files: trays.get(id)?.tray.files() ?? [],
        }));
}

/**
 * A tray per colour, holding that colour's photographs. Mounted after the panel's
 * markup is in the DOM, and returns nothing: in the edit modal the piece already
 * exists, so a photograph chosen here is uploaded at once and the panel is rebuilt
 * from what came back.
 */
export function wireVariantPhotos(product, { onUpload, onRemove }) {
    product.variants.forEach((variant) => {
        const host = document.querySelector(`[data-variant-photos="${variant.id}"]`);
        if (!host) return;

        PhotoPicker.mount(host, {
            multiple: true,
            hint: "Arraste, escolha ou tire",
            initial: (variant.images || []).map((image) => ({
                id: image.id,
                url: image.url,
            })),
            onAdd: (files) => onUpload(variant, files),
            onRemoveStored: (image) => onRemove(image),
        });
    });
}

/**
 * The colours panel inside the edit modal: what the piece is offered in, and each
 * colour's photographs with it.
 *
 * One panel rather than two tabs. Every photograph belongs to a colour, so a tab of
 * colours and a tab of photographs were two views of the same fact — and the
 * photographs tab had to name the colour again in a dropdown to say what it already
 * knew.
 */
export async function variantsPanel(product) {
    const { colorSets } = await reference();
    const used = new Set(product.variants.map((v) => v.color_set.id));
    const available = colorSets.filter((cs) => !used.has(cs.id));

    const rows = product.variants.length
        ? product.variants.map((v) => `
            <li class="list-group-item px-0 d-flex flex-column align-items-stretch"
                data-variant-block="${v.id}">
              <span class="d-flex align-items-center gap-1 mb-2">
                ${ColorSet.badge(v.color_set, "me-auto")}
                <button class="btn btn-sm btn-ghost text-danger"
                        data-remove-variant="${v.id}" title="Remover esta cor"
                        aria-label="Remover ${escapeHtml(v.color_set.name)}">
                  <span class="icon"><i class="fa-solid fa-xmark"></i></span>
                </button>
              </span>
              <div data-variant-photos="${v.id}"></div>
            </li>`).join("")
        : `<li class="text-body-secondary fs-7">
             Sem cores associadas. Escolha uma abaixo — as fotografias são de uma cor.
           </li>`;

    // Photographs belonging to no colour cannot be made any more, but the seeded ones
    // exist. Without a place here they would be invisible again — and invisible is what
    // the owners cannot fix. The block disappears by itself once they are dealt with.
    const orphans = product.images || [];
    const orphanBlock = orphans.length
        ? `<div class="mb-4" id="colourless-photos">
             <!-- Two whole sentences rather than a stem with suffixes spliced in: the
                  first attempt read "Apague -a e volte a carregá-la". -->
             <p class="help fw-medium mb-2">
               ${orphans.length === 1
                   ? "Uma fotografia sem cor. Apague-a e volte a carregá-la na cor a que pertence."
                   : `${orphans.length} fotografias sem cor. Apague-as e volte a carregá-las nas cores a que pertencem.`}
             </p>
             <ul class="list-group list-group-flush">
               ${orphans.map((image) => `
                 <li class="list-group-item px-0 d-flex align-items-center gap-1">
                   <img class="dash-thumb" src="${escapeHtml(image.url)}"
                        alt="${escapeHtml(image.alt ?? "")}">
                   <span class="badge rounded-pill chip is-attention me-auto">Sem cor</span>
                   <button class="btn btn-sm btn-ghost text-danger"
                           data-remove-image="${image.id}" title="Remover"
                           aria-label="Remover esta fotografia sem cor">
                     <span class="icon"><i class="fa-solid fa-xmark"></i></span>
                   </button>
                 </li>`).join("")}
             </ul>
           </div>`
        : "";

    return `
      <ul class="list-group list-group-flush mb-3" id="variant-rows">${rows}</ul>
      ${orphanBlock}
      <div class="input-group input-group-sm">
        <select class="form-select" id="variant-picker"${available.length ? "" : " disabled"}>
          ${available.length
              ? available.map((cs) => `<option value="${cs.id}">${escapeHtml(cs.name)}</option>`).join("")
              : `<option>Todos os conjuntos já estão associados</option>`}
        </select>
        ${fieldIcon("fa-solid fa-palette")}
        <button class="btn btn-dark" id="add-variant"${available.length ? "" : " disabled"}>
          Adicionar
        </button>
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
