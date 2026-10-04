import { API, request } from "../../core/api.js";
import { ColorSet } from "../../store/color-set.js";
import { confirmDialog, formDialog, modal } from "../../core/modal.js";
import { escapeHtml, fieldIcon } from "../../core/html.js";
import { nameTaken } from "../errors.js";
import { picked, pickChip, wirePicks } from "../picks.js";

export function setRow(set, pieces) {
    const names = set.colors.map((c) => c.name).join(", ");

    return `
      <tr data-set-id="${set.id}">
        <td class="dash-col-name">${ColorSet.badge(set)}</td>
        <td class="fs-7 text-body-secondary">${escapeHtml(names || "Sem cores")}</td>
        <td class="fs-7 text-body-secondary">${
            (set.collections ?? []).map((c) => escapeHtml(c.name)).join(", ") || "—"
        }</td>
        <td class="dash-col-photos" data-label="Peças">
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

const colorChip = (color) => `
  <button type="button" class="badge rounded-pill color-chip" data-color-id="${color.id}">
    <span class="swatch" style="background:${escapeHtml(color.hex || "#CCCCCC")}"></span>
    <span>${escapeHtml(color.name)}</span>
  </button>`;

function setForm(set, colors, collections) {
    const mine = new Set((set?.collections ?? []).map((c) => c.id));

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
        <label class="form-label fs-7">Colecções</label>
        <div class="d-flex flex-wrap gap-1" id="sf-collections">
          ${collections.map((c) => pickChip(c.id, c.name, mine.has(c.id))).join("")
            || `<p class="help mb-0">Ainda não há colecções.</p>`}
        </div>
        <p class="help mb-0">
          Onde este conjunto aparece. Pode estar em várias, ou em nenhuma.
        </p>
      </div>

      <div>
        <label class="form-label fs-7">Como vai aparecer na loja</label>
        <div id="sf-preview"></div>
      </div>
    </form>`;
}

function wireSetForm(modalId, set, colors) {
    const form = modal(modalId).querySelector("#set-form");
    const chosen = (set?.colors ?? []).map((c) => c.id);
    const findColor = (id) => colors.find((c) => c.id === Number(id)) ?? null;
    const collectionsBox = form.querySelector("#sf-collections");

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

    wirePicks(collectionsBox);
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
                color_ids: chosen,
                collection_ids: picked(collectionsBox),
            },
        };
    };
}

export function openSetForm({ modalId, set = null, colors, collections, after }) {
    let read;

    formDialog({
        id: modalId,
        body: setForm(set, colors, collections),
        submitLabel: set ? "Guardar alterações" : "Criar conjunto",
        afterRender: () => { read = wireSetForm(modalId, set, colors); },
        onSubmit: async () => {
            const { id, payload } = read();
            try {
                return await request(id ? API.colorSets.update(id) : API.colorSets.create,
                                     { method: id ? "PUT" : "POST", body: payload });
            } catch (error) {
                throw new Error(nameTaken(error, "um conjunto"));
            }
        },
        success: set ? "Conjunto actualizado." : "Conjunto criado.",
        after,
    });
}

export function openDeleteSet({ set, pieces, after }) {
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
        onConfirm: () => request(API.colorSets.delete(set.id), { method: "DELETE" }),
        success: "Conjunto apagado.",
        after,
    });
}
