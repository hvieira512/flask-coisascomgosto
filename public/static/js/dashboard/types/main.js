import { API, list, request } from "../../core/api.js";
import { escapeHtml } from "../../core/html.js";
import { bodyOf, confirmDialog, footOf, formDialog, modal, open } from "../../core/modal.js";
import { Notify } from "../../core/notify.js";
import { mountMaterials } from "./materials.js";

const ICONS = [
    "fa-box", "fa-box-archive", "fa-circle-dot", "fa-heart", "fa-image",
    "fa-circle-notch", "fa-gift", "fa-star", "fa-wine-bottle", "fa-brush",
    "fa-scroll", "fa-key", "fa-magnet", "fa-tag",
];

let types = [];

// The photograph is one of the type's own pieces, borrowed the way the shop's
// family tiles borrow it. Without one the type falls back to the drawing it lends
// its unphotographed pieces, which is the next-best thing it has.
function typeRow(type) {
    const pieces = type.pieces ?? 0;
    const icon = type.icon || "fa-tag";

    const art = type.image
        ? `<img class="dash-thumb" src="${escapeHtml(type.image.url)}"
                alt="${escapeHtml(type.image.alt || type.name)}">`
        : `<span class="disc dash-type-icon">
             <i class="fa-solid ${escapeHtml(icon)}"></i>
           </span>`;

    return `
      <tr data-type-id="${type.id}">
        <td class="dash-col-thumb">${art}</td>
        <td class="dash-col-name">
          <p class="fw-medium mb-0">${escapeHtml(type.name)}</p>
          <p class="help mb-0">${escapeHtml(type.description ?? "—")}</p>
        </td>
        <td data-label="Sem fotografia mostra">
          <span class="d-inline-flex align-items-center gap-2">
            <span class="disc dash-type-icon is-small">
              <i class="fa-solid ${escapeHtml(icon)}"></i>
            </span>
            <span class="data text-body-secondary">${escapeHtml(icon)}</span>
          </span>
        </td>
        <td class="dash-col-photos" data-label="Peças">
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

// The count comes with the type, from the same query the shop's landing page
// asks. It used to be counted in the browser over every product, which the
// hundred-product page limit would eventually have made quietly wrong.
async function loadTypes() {
    const all = await list(API.productTypes.list, "product_types",
                           { fallback: "Erro ao carregar os tipos." });
    types = all;

    const rows = all.map(typeRow);

    document.getElementById("type-rows").innerHTML = rows.length
        ? rows.join("")
        : `<tr><td colspan="5" class="text-center text-body-secondary py-5">
             Ainda não há tipos. Cada peça precisa de um.</td></tr>`;

    const pieces = all.reduce((total, type) => total + (type.pieces ?? 0), 0);
    document.getElementById("type-count").textContent =
        `${all.length} ${all.length === 1 ? "tipo" : "tipos"} · ` +
        `${pieces} ${pieces === 1 ? "peça" : "peças"}`;
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
        </div>
        <p class="help mb-0">
          Desenhado nas peças sem fotografia. <span id="tf-icon-preview"></span>
        </p>
      </div>
    </form>`;
}

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

    const pieces = type.pieces ?? 0;

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
            <a class="btn btn-dark" href="/dashboard/products?tipo=${type.id}">Ver as peças</a>`;
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
mountMaterials().load().catch((error) => Notify.error(error.message));
