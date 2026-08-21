import { API, list, request } from "../../core/api.js";
import { Notify } from "../../core/notify.js";
import { escapeHtml } from "../../core/html.js";
import { nameTaken } from "../errors.js";
import { submitting } from "../../core/modal.js";

/**
 * Materials: what the pieces are made of.
 *
 * A short lookup, edited in place beside the types rather than through dialogs of
 * its own — the owners add one every few months, not every day. Renaming asks for
 * the new name in a prompt for the same reason.
 *
 * Self-contained: nothing else on the page reads a material, so this mounts once
 * and keeps its own list.
 */
export function mountMaterials() {
    const rows = document.getElementById("material-rows");
    const count = document.getElementById("material-count");
    const form = document.getElementById("material-form");

    async function load() {
        const materials = await list(API.materials.list, "materials",
                                     { fallback: "Erro ao carregar os materiais." });

        rows.innerHTML = materials.length
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

        count.textContent = String(materials.length);
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const input = document.getElementById("material-name");
        const name = input.value.trim();
        if (!name) return;

        return submitting(event.submitter ?? event.target.querySelector("button"), async () => {
            try {
                await request(API.materials.create, { method: "POST", body: { name } });
            } catch (error) {
                throw new Error(nameTaken(error, "um material"));
            }
            input.value = "";
            Notify.success("Material adicionado.");
            await load();
        });
    });

    rows.addEventListener("click", async (event) => {
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
                await load();
            } catch (error) {
                Notify.error(nameTaken(error, "um material"));
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
                await load();
            } catch (error) {
                Notify.error(error.message);
            }
        }
    });

    return { load };
}
