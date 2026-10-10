import { API, request } from "../../core/api.js";
import { ColorSet } from "../../store/color-set.js";
import { PhotoPicker } from "../../core/photo-picker.js";
import { escapeHtml } from "../../core/html.js";
import { reference } from "./reference.js";

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

        [...trays.keys()].forEach((id) => {
            if (ids.includes(id)) return;
            trays.get(id).row.remove();
            trays.delete(id);
        });

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

    return `
      <ul class="list-group list-group-flush mb-3" id="variant-rows">${rows}</ul>
      <div class="input-group input-group-sm">
        <select class="form-select" id="variant-picker"${available.length ? "" : " disabled"}>
          ${available.length
              ? available.map((cs) => `<option value="${cs.id}">${escapeHtml(cs.name)}</option>`).join("")
              : `<option>Todos os conjuntos já estão associados</option>`}
        </select>
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
