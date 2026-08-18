import { bodyOf, close, footOf, modal, open, submitting } from "../../core/modal.js";
import {
    countByType, createMaterial, createType, deleteMaterial, deleteType,
    listMaterials, listTypes, updateMaterial, updateType,
} from "./api.js";

/**
 * Tipos e materiais.
 *
 * The type tree is the page's subject — every piece must have a type — so it
 * takes the table. Sub-types are shown indented under their parent rather than in
 * a separate list, because "Caixa redonda" means nothing without "Caixa" above
 * it. Materials are a short lookup edited in place beside it.
 */

// Enough to cover the workshop's vocabulary without a picker.
const ICONS = [
    "fa-box", "fa-box-archive", "fa-circle-dot", "fa-heart", "fa-image",
    "fa-circle-notch", "fa-gift", "fa-star", "fa-wine-bottle", "fa-brush",
    "fa-scroll", "fa-key", "fa-magnet", "fa-tag",
];

let types = [];
let pieceCounts = new Map();

function typeRow(type, { parent = null } = {}) {
    const pieces = type.pieces ?? 0;
    const isSub = Boolean(parent);

    return `
      <tr data-type-id="${type.id}">
        <td>
          <span class="disc dash-type-icon">
            <i class="fa-solid ${escapeHtml(type.icon || parent?.icon || "fa-tag")}"></i>
          </span>
        </td>
        <td>
          <p class="has-text-weight-medium${isSub ? " dash-subtype" : ""}">
            ${escapeHtml(type.name)}
          </p>
          ${isSub
              ? `<p class="is-size-7 has-text-grey dash-subtype">em ${escapeHtml(parent.name)}</p>`
              : `<p class="is-size-7 has-text-grey">
                   ${type.sub_types?.length
                       ? `${type.sub_types.length} ${type.sub_types.length === 1 ? "sub-tipo" : "sub-tipos"}`
                       : "Sem sub-tipos"}
                 </p>`}
        </td>
        <td class="is-size-7 has-text-grey">${escapeHtml(type.description ?? "—")}</td>
        <td>
          ${pieces
              ? `<span class="data has-text-grey">${pieces} ${pieces === 1 ? "peça" : "peças"}</span>`
              : `<span class="tag is-rounded chip is-quiet">Sem peças</span>`}
        </td>
        <td class="dash-col-actions">
          <span class="dash-row-actions is-flex is-gap-1">
            ${isSub ? "" : `
              <button class="button is-small is-ghost" data-type-action="add-sub"
                      data-type-id="${type.id}" title="Adicionar sub-tipo"
                      aria-label="Adicionar sub-tipo a ${escapeHtml(type.name)}">
                <span class="icon"><i class="fa-solid fa-plus"></i></span>
              </button>`}
            <button class="button is-small is-ghost" data-type-action="edit"
                    data-type-id="${type.id}" title="Editar"
                    aria-label="Editar ${escapeHtml(type.name)}">
              <span class="icon"><i class="fa-solid fa-pencil"></i></span>
            </button>
            <button class="button is-small is-ghost has-text-danger" data-type-action="delete"
                    data-type-id="${type.id}" title="Apagar"
                    aria-label="Apagar ${escapeHtml(type.name)}">
              <span class="icon"><i class="fa-solid fa-trash"></i></span>
            </button>
          </span>
        </td>
      </tr>`;
}

async function loadTypes() {
    const [roots, counts] = await Promise.all([listTypes(), countByType()]);
    pieceCounts = counts;

    // Flattened for the table, but each sub-type keeps a reference to its parent
    // so a row can show where it belongs and hide the actions that make no sense.
    types = roots;
    const rows = roots.flatMap((root) => [
        typeRow({ ...root, pieces: counts.get(root.id) ?? 0 }),
        ...(root.sub_types ?? []).map((sub) =>
            typeRow({ ...sub, pieces: counts.get(sub.id) ?? 0 }, { parent: root })
        ),
    ]);

    document.getElementById("type-rows").innerHTML = rows.length
        ? rows.join("")
        : `<tr><td colspan="5" class="has-text-centered has-text-grey py-6">
             Ainda não há tipos. Cada peça precisa de um.</td></tr>`;

    const total = roots.length + roots.reduce((n, r) => n + (r.sub_types?.length ?? 0), 0);
    document.getElementById("type-count").textContent =
        `${total} ${total === 1 ? "tipo" : "tipos"}`;
}

function findType(id) {
    const wanted = Number(id);
    for (const root of types) {
        if (root.id === wanted) return { type: root, parent: null };
        const sub = (root.sub_types ?? []).find((s) => s.id === wanted);
        if (sub) return { type: sub, parent: root };
    }
    return { type: null, parent: null };
}

function typeForm(type = null, parent = null) {
    const iconOptions = ICONS.map((icon) =>
        `<option value="${icon}"${type?.icon === icon ? " selected" : ""}>${icon}</option>`
    ).join("");

    return `
    <form id="type-form" data-type-id="${type?.id ?? ""}" data-parent-id="${parent?.id ?? ""}">
      ${parent
          ? `<p class="mb-4 is-size-7 has-text-grey">
               Sub-tipo de <strong>${escapeHtml(parent.name)}</strong>.
             </p>`
          : ""}

      <div class="field">
        <label class="label is-small" for="tf-name">Nome</label>
        <input class="input" id="tf-name" name="name" required
               value="${escapeHtml(type?.name ?? "")}"
               placeholder="${parent ? "Caixa redonda" : "Caixa"}">
      </div>

      <div class="field">
        <label class="label is-small" for="tf-description">Descrição</label>
        <textarea class="textarea" id="tf-description" name="description" rows="2"
                  placeholder="O que é esta família de peças."
                  >${escapeHtml(type?.description ?? "")}</textarea>
      </div>

      <div class="field">
        <label class="label is-small" for="tf-icon">Ícone</label>
        <div class="select is-fullwidth">
          <select id="tf-icon" name="icon">
            <option value="">${parent ? "Herdar do tipo acima" : "Adivinhar pelo nome"}</option>
            ${iconOptions}
          </select>
        </div>
        <p class="help">
          Desenhado nas peças sem fotografia. <span id="tf-icon-preview"></span>
        </p>
      </div>
    </form>`;
}

/** The chosen icon, drawn next to the picker, so the choice is not a guess. */
function wireIconPreview(modalId) {
    const select = modal(modalId).querySelector("#tf-icon");
    const preview = modal(modalId).querySelector("#tf-icon-preview");

    const draw = () => {
        preview.innerHTML = select.value
            ? `<span class="icon"><i class="fa-solid ${escapeHtml(select.value)}"></i></span>`
            : "";
    };
    select.addEventListener("change", draw);
    draw();
}

function payloadFrom(modalId) {
    const form = modal(modalId).querySelector("#type-form");
    const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();

    const payload = { name: value("name") };
    if (!payload.name) throw new Error("O nome é obrigatório.");

    // The API rejects an explicit null, so an empty field is omitted instead.
    if (value("description")) payload.description = value("description");
    if (value("icon")) payload.icon = value("icon");
    if (form.dataset.parentId) payload.parent_id = Number(form.dataset.parentId);

    return { id: form.dataset.typeId, payload };
}

function openTypeForm({ modalId, type = null, parent = null }) {
    bodyOf(modalId).innerHTML = typeForm(type, parent);
    footOf(modalId).innerHTML = `
        <button class="button" data-modal-close>Cancelar</button>
        <button class="button is-dark" id="type-submit">
          ${type ? "Guardar alterações" : "Criar tipo"}
        </button>`;
    open(modalId);
    wireIconPreview(modalId);

    document.getElementById("type-submit").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            const { id, payload } = payloadFrom(modalId);
            if (id) {
                await updateType(id, payload);
            } else {
                await createType(payload);
            }
            close(modalId);
            Notify.success(type ? "Tipo actualizado." : "Tipo criado.");
            await loadTypes();
        });
}

/** Pieces filed under a type or any of its sub-types — what a delete blocks. */
function piecesUnder(type) {
    const own = pieceCounts.get(type.id) ?? 0;
    const subs = (type.sub_types ?? []).reduce(
        (n, sub) => n + (pieceCounts.get(sub.id) ?? 0), 0
    );
    return own + subs;
}

async function openDeleteType(id) {
    const { type } = findType(id);
    if (!type) return;

    const subs = type.sub_types?.length ?? 0;
    const pieces = piecesUnder(type);

    // A type in use cannot be deleted — every piece needs one. Saying so here,
    // and withholding the button, beats offering an action that can only fail
    // and then relaying the API's English back to the owner.
    if (pieces) {
        bodyOf("deleteTypeModal").innerHTML = `
            <p><strong>${escapeHtml(type.name)}</strong> ainda tem
               ${pieces} ${pieces === 1 ? "peça" : "peças"}.</p>
            <p class="has-text-grey is-size-7 mt-2">
              Cada peça tem de ter um tipo, por isso este não pode ser apagado.
              Mude essas peças para outro tipo primeiro, no separador Produtos.
            </p>`;
        footOf("deleteTypeModal").innerHTML = `
            <button class="button" data-modal-close>Fechar</button>
            <a class="button is-dark" href="/dashboard/products">Ver as peças</a>`;
        open("deleteTypeModal");
        return;
    }

    bodyOf("deleteTypeModal").innerHTML = `
        <p>Apagar <strong>${escapeHtml(type.name)}</strong>?</p>
        ${subs
            ? `<p class="has-text-grey is-size-7 mt-2">
                 Apaga também ${subs === 1 ? "o seu sub-tipo" : `os seus ${subs} sub-tipos`}.
               </p>`
            : ""}`;
    footOf("deleteTypeModal").innerHTML = `
        <button class="button" data-modal-close>Cancelar</button>
        <button class="button is-danger" id="type-delete">Apagar</button>`;
    open("deleteTypeModal");

    document.getElementById("type-delete").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            await deleteType(id);
            close("deleteTypeModal");
            Notify.success("Tipo apagado.");
            await loadTypes();
        });
}

// ---- Materials ----

async function loadMaterials() {
    const materials = await listMaterials();

    document.getElementById("material-rows").innerHTML = materials.length
        ? `<ul class="panel is-shadowless mb-0">${materials
              .map((m) => `
                <li class="panel-block px-0 is-justify-content-space-between">
                  <span data-material-name="${m.id}">${escapeHtml(m.name)}</span>
                  <span class="dash-row-actions is-flex is-gap-1">
                    <button class="button is-small is-ghost" data-material-action="rename"
                            data-material-id="${m.id}" title="Mudar o nome"
                            aria-label="Mudar o nome de ${escapeHtml(m.name)}">
                      <span class="icon"><i class="fa-solid fa-pencil"></i></span>
                    </button>
                    <button class="button is-small is-ghost has-text-danger"
                            data-material-action="delete" data-material-id="${m.id}"
                            title="Apagar" aria-label="Apagar ${escapeHtml(m.name)}">
                      <span class="icon"><i class="fa-solid fa-xmark"></i></span>
                    </button>
                  </span>
                </li>`)
              .join("")}</ul>`
        : `<p class="has-text-grey is-size-7">Ainda não há materiais.</p>`;

    document.getElementById("material-count").textContent = String(materials.length);
}

document.getElementById("material-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.getElementById("material-name");

    return submitting(event.submitter ?? event.target.querySelector("button"), async () => {
        await createMaterial(input.value.trim());
        input.value = "";
        Notify.success("Material adicionado.");
        await loadMaterials();
    });
});

document.getElementById("material-rows").addEventListener("click", async (event) => {
    const trigger = event.target.closest("[data-material-action]");
    if (!trigger) return;

    const { materialAction: action, materialId: id } = trigger.dataset;
    const current = document
        .querySelector(`[data-material-name="${id}"]`)
        .textContent.trim();

    if (action === "rename") {
        const name = await Notify.prompt("Novo nome", { value: current });
        if (!name || name === current) return;
        try {
            await updateMaterial(id, name);
            Notify.success("Material actualizado.");
            await loadMaterials();
        } catch (error) {
            Notify.error(error.message);
        }
        return;
    }

    if (action === "delete") {
        const ok = await Notify.confirm(`Apagar "${current}"?`, {
            text: "As peças feitas deste material ficam sem material.",
            danger: true,
            confirmText: "Apagar",
        });
        if (!ok) return;
        try {
            await deleteMaterial(id);
            Notify.success("Material apagado.");
            await loadMaterials();
        } catch (error) {
            Notify.error(error.message);
        }
    }
});

// ---- Wiring ----

document.getElementById("type-rows").addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-type-action]");
    if (trigger) {
        const { typeAction: action, typeId: id } = trigger.dataset;
        const { type, parent } = findType(id);

        if (action === "edit") openTypeForm({ modalId: "editTypeModal", type, parent });
        if (action === "add-sub") openTypeForm({ modalId: "newTypeModal", parent: type });
        if (action === "delete") openDeleteType(id);
        return;
    }

    const row = event.target.closest("tr[data-type-id]");
    if (row) {
        const { type, parent } = findType(row.dataset.typeId);
        openTypeForm({ modalId: "editTypeModal", type, parent });
    }
});

document.getElementById("new-type").addEventListener("click", () =>
    openTypeForm({ modalId: "newTypeModal" })
);

loadTypes().catch((error) => Notify.error(error.message));
loadMaterials().catch((error) => Notify.error(error.message));
