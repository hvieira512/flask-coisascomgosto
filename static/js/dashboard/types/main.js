import { API, list, request } from "../../core/api.js";
import { escapeHtml, fieldIcon } from "../../core/html.js";
import { bodyOf, confirmDialog, footOf, formDialog, modal, open, submitting } from "../../core/modal.js";
import { Notify } from "../../core/notify.js";
import { byType } from "../counts.js";

/**
 * Tipos e materiais.
 *
 * Types are the page's subject — every piece must have one — so they take the
 * table. The list is flat: a type is the family ("Caixa"), and the shape lives
 * in the piece's own name. Materials are a short lookup edited in place beside
 * it.
 */

// Enough to cover the workshop's vocabulary without a picker.
const ICONS = [
    "fa-box", "fa-box-archive", "fa-circle-dot", "fa-heart", "fa-image",
    "fa-circle-notch", "fa-gift", "fa-star", "fa-wine-bottle", "fa-brush",
    "fa-scroll", "fa-key", "fa-magnet", "fa-tag",
];

let types = [];
let pieceCounts = new Map();

function typeRow(type) {
    const pieces = type.pieces ?? 0;

    return `
      <tr data-type-id="${type.id}">
        <td>
          <span class="disc dash-type-icon">
            <i class="fa-solid ${escapeHtml(type.icon || "fa-tag")}"></i>
          </span>
        </td>
        <td>
          <p class="fw-medium mb-0">${escapeHtml(type.name)}</p>
        </td>
        <td class="fs-7 text-body-secondary">${escapeHtml(type.description ?? "—")}</td>
        <td>
          ${pieces
              ? `<span class="data text-body-secondary">${pieces} ${pieces === 1 ? "peça" : "peças"}</span>`
              : `<span class="badge rounded-pill chip is-quiet">Sem peças</span>`}
        </td>
        <td class="dash-col-actions">
          <span class="dash-row-actions d-flex gap-1">
            <button class="btn btn-sm btn-ghost" data-type-action="edit"
                    data-type-id="${type.id}" title="Editar"
                    aria-label="Editar ${escapeHtml(type.name)}">
              <span class="icon"><i class="fa-solid fa-pencil"></i></span>
            </button>
            <button class="btn btn-sm btn-ghost text-danger" data-type-action="delete"
                    data-type-id="${type.id}" title="Apagar"
                    aria-label="Apagar ${escapeHtml(type.name)}">
              <span class="icon"><i class="fa-solid fa-trash"></i></span>
            </button>
          </span>
        </td>
      </tr>`;
}

async function loadTypes() {
    const [all, counts] = await Promise.all([
        list(API.productTypes.list, "product_types",
             { fallback: "Erro ao carregar os tipos." }),
        byType(),
    ]);
    pieceCounts = counts;
    types = all;

    const rows = all.map((type) =>
        typeRow({ ...type, pieces: counts.get(type.id) ?? 0 })
    );

    document.getElementById("type-rows").innerHTML = rows.length
        ? rows.join("")
        : `<tr><td colspan="5" class="text-center text-body-secondary py-5">
             Ainda não há tipos. Cada peça precisa de um.</td></tr>`;

    document.getElementById("type-count").textContent =
        `${all.length} ${all.length === 1 ? "tipo" : "tipos"}`;
}

const findType = (id) => types.find((type) => type.id === Number(id)) ?? null;

function typeForm(type = null) {
    const iconOptions = ICONS.map((icon) =>
        `<option value="${icon}"${type?.icon === icon ? " selected" : ""}>${icon}</option>`
    ).join("");

    return `
    <form id="type-form" data-type-id="${type?.id ?? ""}">
      <div class="mb-3">
        <label class="form-label fs-7" for="tf-name">Nome</label>
        <div class="input-group">
          <input class="form-control" id="tf-name" name="name" required
                 value="${escapeHtml(type?.name ?? "")}" placeholder="Caixa">
          ${fieldIcon("fa-solid fa-tag")}
        </div>
        <p class="help mb-0">
          A família da peça. A forma vai no nome da peça — "Caixa rectangular".
        </p>
      </div>

      <div class="mb-3">
        <label class="form-label fs-7" for="tf-description">Descrição</label>
        <textarea class="form-control" id="tf-description" name="description" rows="2"
                  placeholder="O que é esta família de peças."
                  >${escapeHtml(type?.description ?? "")}</textarea>
      </div>

      <div>
        <label class="form-label fs-7" for="tf-icon">Ícone</label>
        <div class="input-group">
          <select class="form-select" id="tf-icon" name="icon">
            <option value="">Adivinhar pelo nome</option>
            ${iconOptions}
          </select>
          ${fieldIcon("fa-solid fa-icons")}
        </div>
        <p class="help mb-0">
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

    return { id: form.dataset.typeId, payload };
}

function openTypeForm({ modalId, type = null }) {
    formDialog({
        id: modalId,
        body: typeForm(type),
        submitLabel: type ? "Guardar alterações" : "Criar tipo",
        afterRender: () => wireIconPreview(modalId),
        onSubmit: async () => {
            const { id, payload } = payloadFrom(modalId);
            return request(id ? API.productTypes.update(id) : API.productTypes.create,
                           { method: id ? "PUT" : "POST", body: payload });
        },
        success: type ? "Tipo actualizado." : "Tipo criado.",
        after: loadTypes,
    });
}

async function openDeleteType(id) {
    const type = findType(id);
    if (!type) return;

    const pieces = pieceCounts.get(type.id) ?? 0;

    // A type in use cannot be deleted — every piece needs one. Saying so here,
    // and withholding the button, beats offering an action that can only fail
    // and then relaying the API's English back to the owner.
    if (pieces) {
        bodyOf("deleteTypeModal").innerHTML = `
            <p><strong>${escapeHtml(type.name)}</strong> ainda tem
               ${pieces} ${pieces === 1 ? "peça" : "peças"}.</p>
            <p class="text-body-secondary fs-7 mt-2">
              Cada peça tem de ter um tipo, por isso este não pode ser apagado.
              Mude essas peças para outro tipo primeiro, no separador Produtos.
            </p>`;
        footOf("deleteTypeModal").innerHTML = `
            <button class="btn btn-outline-secondary" data-bs-dismiss="modal">Fechar</button>
            <a class="btn btn-dark" href="/dashboard/products">Ver as peças</a>`;
        open("deleteTypeModal");
        return;
    }

    confirmDialog({
        id: "deleteTypeModal",
        body: `<p>Apagar <strong>${escapeHtml(type.name)}</strong>?</p>`,
        onConfirm: () => request(API.productTypes.delete(id), { method: "DELETE" }),
        success: "Tipo apagado.",
        after: loadTypes,
    });
}

// ---- Materials ----

async function loadMaterials() {
    const materials = await list(API.materials.list, "materials",
                                 { fallback: "Erro ao carregar os materiais." });

    document.getElementById("material-rows").innerHTML = materials.length
        ? `<ul class="list-group list-group-flush">${materials
              .map((m) => `
                <li class="list-group-item px-0 d-flex justify-content-between align-items-center">
                  <span data-material-name="${m.id}">${escapeHtml(m.name)}</span>
                  <span class="dash-row-actions d-flex gap-1">
                    <button class="btn btn-sm btn-ghost" data-material-action="rename"
                            data-material-id="${m.id}" title="Mudar o nome"
                            aria-label="Mudar o nome de ${escapeHtml(m.name)}">
                      <span class="icon"><i class="fa-solid fa-pencil"></i></span>
                    </button>
                    <button class="btn btn-sm btn-ghost text-danger"
                            data-material-action="delete" data-material-id="${m.id}"
                            title="Apagar" aria-label="Apagar ${escapeHtml(m.name)}">
                      <span class="icon"><i class="fa-solid fa-xmark"></i></span>
                    </button>
                  </span>
                </li>`)
              .join("")}</ul>`
        : `<p class="text-body-secondary fs-7">Ainda não há materiais.</p>`;

    document.getElementById("material-count").textContent = String(materials.length);
}

/** The API answers a duplicate in English; the owners read Portuguese. */
const materialError = (error) =>
    error.status === 409
        ? "Já existe um material com esse nome."
        : error.message;

document.getElementById("material-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.getElementById("material-name");
    const name = input.value.trim();
    if (!name) return;

    return submitting(event.submitter ?? event.target.querySelector("button"), async () => {
        try {
            await request(API.materials.create, { method: "POST", body: { name } });
        } catch (error) {
            throw new Error(materialError(error));
        }
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
        const name = await Notify.prompt("Novo nome do material", { value: current });
        if (!name || name.trim() === current) return;
        try {
            await request(API.materials.update(id),
                          { method: "PUT", body: { name: name.trim() } });
            Notify.success("Material actualizado.");
            await loadMaterials();
        } catch (error) {
            Notify.error(materialError(error));
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
            await request(API.materials.delete(id), { method: "DELETE" });
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

        if (action === "edit") openTypeForm({ modalId: "editTypeModal", type: findType(id) });
        if (action === "delete") openDeleteType(id);
        return;
    }

    const row = event.target.closest("tr[data-type-id]");
    if (row) {
        openTypeForm({ modalId: "editTypeModal", type: findType(row.dataset.typeId) });
    }
});

document.getElementById("new-type").addEventListener("click", () =>
    openTypeForm({ modalId: "newTypeModal" })
);

loadTypes().catch((error) => Notify.error(error.message));
loadMaterials().catch((error) => Notify.error(error.message));
