import { escapeHtml, fieldIcon } from "../../core/html.js";
import { confirmDialog, formDialog, modal, submitting } from "../../core/modal.js";
import { Notify } from "../../core/notify.js";
import { ColorSet } from "../../store/color-set.js";
import {
    countByColorSet, createColor, createColorSet, deleteColor, deleteColorSet,
    listCollections, listColorSets, listColors, updateColor, updateColorSet,
} from "./api.js";

/**
 * Cores e conjuntos.
 *
 * A conjunto is what the storefront calls a colour combination — "Branco e
 * Dourado" — and a variant is a piece offered in one. The sets take the table;
 * the individual colours are a short lookup beside it, since they only exist to
 * be combined.
 */

let sets = [];
let colors = [];
let collections = [];
let pieceCounts = new Map();

const findSet = (id) => sets.find((s) => s.id === Number(id)) ?? null;
const findColor = (id) => colors.find((c) => c.id === Number(id)) ?? null;

// ---- Colour sets ----

function setRow(set) {
    const pieces = pieceCounts.get(set.id) ?? 0;
    const names = set.colors.map((c) => c.name).join(", ");

    return `
      <tr data-set-id="${set.id}">
        <td>${ColorSet.badge(set)}</td>
        <td class="fs-7 text-body-secondary">${escapeHtml(names || "Sem cores")}</td>
        <td class="fs-7 text-body-secondary">${escapeHtml(set.collection?.name ?? "—")}</td>
        <td>
          ${pieces
              ? `<span class="data text-body-secondary">${pieces} ${pieces === 1 ? "peça" : "peças"}</span>`
              : `<span class="badge rounded-pill chip is-quiet">Sem peças</span>`}
        </td>
        <td class="dash-col-actions">
          <span class="dash-row-actions d-flex gap-1">
            <button class="btn btn-sm btn-ghost" data-set-action="edit"
                    data-set-id="${set.id}" title="Editar"
                    aria-label="Editar ${escapeHtml(set.name)}">
              <span class="icon"><i class="fa-solid fa-pencil"></i></span>
            </button>
            <button class="btn btn-sm btn-ghost text-danger" data-set-action="delete"
                    data-set-id="${set.id}" title="Apagar"
                    aria-label="Apagar ${escapeHtml(set.name)}">
              <span class="icon"><i class="fa-solid fa-trash"></i></span>
            </button>
          </span>
        </td>
      </tr>`;
}

async function loadSets() {
    const [all, counts] = await Promise.all([listColorSets(), countByColorSet()]);
    pieceCounts = counts;
    sets = all;

    document.getElementById("set-rows").innerHTML = all.length
        ? all.map(setRow).join("")
        : `<tr><td colspan="5" class="text-center text-body-secondary py-5">
             Ainda não há conjuntos. Cada peça é oferecida num deles.</td></tr>`;

    document.getElementById("set-count").textContent =
        `${all.length} ${all.length === 1 ? "conjunto" : "conjuntos"}`;
}

function setForm(set = null) {
    const options = collections
        .map((c) => `<option value="${c.id}"${set?.collection?.id === c.id ? " selected" : ""}>
                       ${escapeHtml(c.name)}</option>`)
        .join("");

    return `
    <form id="set-form" data-set-id="${set?.id ?? ""}">
      <div class="mb-3">
        <label class="form-label fs-7" for="sf-name">Nome</label>
        <div class="input-group">
          <input class="form-control" id="sf-name" name="name" required
                 value="${escapeHtml(set?.name ?? "")}" placeholder="Branco e Dourado">
          ${fieldIcon("fa-solid fa-tag")}
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label fs-7">Cores</label>
        <div class="d-flex flex-wrap gap-1" id="sf-colors">
          ${colors.map(colorChip).join("") || `<p class="help">Adicione cores primeiro.</p>`}
        </div>
        <p class="help mb-0">
          Pela ordem em que as escolher — a primeira dá o tom ao conjunto.
        </p>
      </div>

      <div class="mb-3">
        <label class="form-label fs-7" for="sf-collection">Colecção</label>
        <div class="input-group">
          <select class="form-select" id="sf-collection" name="collection_id">
            <option value="">Sem colecção</option>
            ${options}
          </select>
          ${fieldIcon("fa-solid fa-layer-group")}
        </div>
      </div>

      <div>
        <label class="form-label fs-7">Como vai aparecer na loja</label>
        <div id="sf-preview"></div>
      </div>
    </form>`;
}

function colorChip(color) {
    return `
      <button type="button" class="badge rounded-pill color-chip" data-color-id="${color.id}">
        <span class="swatch" style="background:${escapeHtml(color.hex || "#CCCCCC")}"></span>
        <span>${escapeHtml(color.name)}</span>
      </button>`;
}

/**
 * The picker, the preview and the chosen order, wired together.
 *
 * Order is the click order rather than the colours' own: "Branco e Dourado" and
 * "Dourado e Branco" are different sets, and the first colour is the one the
 * badge takes its tint from.
 */
function wireSetForm(modalId, set) {
    const form = modal(modalId).querySelector("#set-form");
    const chosen = (set?.colors ?? []).map((c) => c.id);

    const draw = () => {
        for (const chip of form.querySelectorAll(".color-chip")) {
            const position = chosen.indexOf(Number(chip.dataset.colorId));
            chip.classList.toggle("is-active", position !== -1);
            chip.setAttribute("aria-pressed", String(position !== -1));
        }

        form.querySelector("#sf-preview").innerHTML = ColorSet.badge({
            name: form.querySelector("#sf-name").value.trim() || "Sem nome",
            colors: chosen.map(findColor).filter(Boolean),
        });
    };

    form.querySelector("#sf-colors").addEventListener("click", (event) => {
        const chip = event.target.closest(".color-chip");
        if (!chip) return;

        const id = Number(chip.dataset.colorId);
        const position = chosen.indexOf(id);
        if (position === -1) chosen.push(id);
        else chosen.splice(position, 1);
        draw();
    });

    form.querySelector("#sf-name").addEventListener("input", draw);
    draw();

    return () => {
        const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();
        if (!value("name")) throw new Error("O nome é obrigatório.");
        if (!chosen.length) throw new Error("Escolha pelo menos uma cor.");

        return {
            id: form.dataset.setId,
            payload: {
                name: value("name"),
                // The API rejects an explicit null, so a set with no collection
                // omits the field.
                ...(value("collection_id")
                    ? { collection_id: Number(value("collection_id")) }
                    : {}),
                color_ids: chosen,
            },
        };
    };
}

/** The API answers a duplicate in English; the owners read Portuguese. */
const nameTaken = (error, what) =>
    error.status === 409 ? `Já existe ${what} com esse nome.` : error.message;

function openSetForm({ modalId, set = null }) {
    let read;

    formDialog({
        id: modalId,
        body: setForm(set),
        submitLabel: set ? "Guardar alterações" : "Criar conjunto",
        afterRender: () => { read = wireSetForm(modalId, set); },
        onSubmit: async () => {
            const { id, payload } = read();
            try {
                return id ? await updateColorSet(id, payload) : await createColorSet(payload);
            } catch (error) {
                throw new Error(nameTaken(error, "um conjunto"));
            }
        },
        success: set ? "Conjunto actualizado." : "Conjunto criado.",
        after: loadSets,
    });
}

function openDeleteSet(id) {
    const set = findSet(id);
    if (!set) return;

    const pieces = pieceCounts.get(set.id) ?? 0;

    // Deleting a set deletes every variant offered in it, and a variant's photos
    // go with it. Unlike a type, this is allowed — so the number is the warning.
    const warning = pieces
        ? `<p class="text-body-secondary fs-7 mt-2">
             ${pieces} ${pieces === 1 ? "peça é oferecida" : "peças são oferecidas"}
             neste conjunto. ${pieces === 1 ? "Essa oferta" : "Essas ofertas"}
             e as respectivas fotografias também desaparecem.
           </p>`
        : "";

    confirmDialog({
        id: "deleteSetModal",
        body: `<p>Apagar <strong>${escapeHtml(set.name)}</strong>?</p>${warning}`,
        onConfirm: () => deleteColorSet(id),
        success: "Conjunto apagado.",
        after: loadSets,
    });
}

// ---- Colours ----

async function loadColors() {
    colors = await listColors();

    document.getElementById("color-rows").innerHTML = colors.length
        ? `<ul class="list-group list-group-flush">${colors
              .map((color) => `
                <li class="list-group-item px-0 d-flex justify-content-between align-items-center">
                  <span class="d-flex align-items-center gap-1">
                    <span class="swatch" style="background:${escapeHtml(color.hex || "#CCCCCC")}"></span>
                    <span data-color-name="${color.id}">${escapeHtml(color.name)}</span>
                  </span>
                  <span class="dash-row-actions d-flex gap-1">
                    <button class="btn btn-sm btn-ghost" data-color-action="edit"
                            data-color-id="${color.id}" title="Editar"
                            aria-label="Editar ${escapeHtml(color.name)}">
                      <span class="icon"><i class="fa-solid fa-pencil"></i></span>
                    </button>
                    <button class="btn btn-sm btn-ghost text-danger"
                            data-color-action="delete" data-color-id="${color.id}"
                            title="Apagar" aria-label="Apagar ${escapeHtml(color.name)}">
                      <span class="icon"><i class="fa-solid fa-xmark"></i></span>
                    </button>
                  </span>
                </li>`)
              .join("")}</ul>`
        : `<p class="text-body-secondary fs-7">Ainda não há cores.</p>`;

    document.getElementById("color-count").textContent = String(colors.length);
}

function openColorForm(color) {
    formDialog({
        id: "editColorModal",
        body: `
          <form id="color-edit-form">
            <div class="mb-3">
              <label class="form-label fs-7" for="cf-name">Nome</label>
              <div class="input-group">
                <input class="form-control" id="cf-name" required value="${escapeHtml(color.name)}">
                ${fieldIcon("fa-solid fa-tag")}
              </div>
            </div>
            <div>
              <label class="form-label fs-7" for="cf-hex">Cor</label>
              <input class="form-control form-control-color" type="color" id="cf-hex"
                     value="${escapeHtml(color.hex || "#CCCCCC")}">
            </div>
          </form>`,
        submitLabel: "Guardar alterações",
        onSubmit: async (dialog) => {
            const name = dialog.querySelector("#cf-name").value.trim();
            if (!name) throw new Error("O nome é obrigatório.");
            try {
                return await updateColor(color.id, {
                    name,
                    hex: dialog.querySelector("#cf-hex").value,
                });
            } catch (error) {
                throw new Error(nameTaken(error, "uma cor"));
            }
        },
        success: "Cor actualizada.",
        // A renamed or recoloured colour shows up inside every set that uses it.
        after: async () => { await loadColors(); await loadSets(); },
    });
}

function openDeleteColor(color) {
    const using = sets.filter((set) => set.colors.some((c) => c.id === color.id));

    const warning = using.length
        ? `<p class="text-body-secondary fs-7 mt-2">
             Sai ${using.length === 1 ? "do conjunto" : "dos conjuntos"}
             ${using.map((set) => `<strong>${escapeHtml(set.name)}</strong>`).join(", ")},
             que ${using.length === 1 ? "fica" : "ficam"} com menos uma cor.
           </p>`
        : "";

    confirmDialog({
        id: "deleteColorModal",
        body: `<p>Apagar <strong>${escapeHtml(color.name)}</strong>?</p>${warning}`,
        onConfirm: () => deleteColor(color.id),
        success: "Cor apagada.",
        after: async () => { await loadColors(); await loadSets(); },
    });
}

// ---- Wiring ----

document.getElementById("color-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const nameInput = document.getElementById("color-name");
    const name = nameInput.value.trim();
    if (!name) return;

    return submitting(event.submitter ?? event.target.querySelector("button"), async () => {
        try {
            await createColor({ name, hex: document.getElementById("color-hex").value });
        } catch (error) {
            throw new Error(nameTaken(error, "uma cor"));
        }
        nameInput.value = "";
        Notify.success("Cor adicionada.");
        await loadColors();
    });
});

document.getElementById("color-rows").addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-color-action]");
    if (!trigger) return;

    const color = findColor(trigger.dataset.colorId);
    if (!color) return;

    if (trigger.dataset.colorAction === "edit") openColorForm(color);
    if (trigger.dataset.colorAction === "delete") openDeleteColor(color);
});

document.getElementById("set-rows").addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-set-action]");
    if (trigger) {
        const { setAction: action, setId: id } = trigger.dataset;

        if (action === "edit") openSetForm({ modalId: "editSetModal", set: findSet(id) });
        if (action === "delete") openDeleteSet(id);
        return;
    }

    const row = event.target.closest("tr[data-set-id]");
    if (row) openSetForm({ modalId: "editSetModal", set: findSet(row.dataset.setId) });
});

document.getElementById("new-set").addEventListener("click", () =>
    openSetForm({ modalId: "newSetModal" })
);

// Colours load first: the set form's picker is built from them.
loadColors()
    .then(async () => { collections = await listCollections(); })
    .then(loadSets)
    .catch((error) => Notify.error(error.message));
