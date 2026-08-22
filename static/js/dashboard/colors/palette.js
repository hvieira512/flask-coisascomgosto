import { API, request } from "../../core/api.js";
import { confirmDialog, formDialog } from "../../core/modal.js";
import { escapeHtml, fieldIcon } from "../../core/html.js";
import { nameTaken } from "../errors.js";

export const colorList = (colors) =>
    colors.length
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

export function openColorForm({ color, after }) {
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
                return await request(API.colors.update(color.id), {
                    method: "PUT",
                    body: { name, hex: dialog.querySelector("#cf-hex").value },
                });
            } catch (error) {
                throw new Error(nameTaken(error, "uma cor"));
            }
        },
        success: "Cor actualizada.",
        after,
    });
}

export function openDeleteColor({ color, using, after }) {
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
        onConfirm: () => request(API.colors.delete(color.id), { method: "DELETE" }),
        success: "Cor apagada.",
        after,
    });
}
