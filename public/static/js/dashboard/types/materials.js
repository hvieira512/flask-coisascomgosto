import { API, list, request } from "../../core/api.js";
import { Notify } from "../../core/notify.js";
import { escapeHtml } from "../../core/html.js";
import { nameTaken } from "../errors.js";
import { submitting } from "../../core/modal.js";

export function mountMaterials() {
    const rows = document.getElementById("material-rows");
    const count = document.getElementById("material-count");
    const form = document.getElementById("material-form");

    async function load() {
        // The counts come from the products' facets, which count in SQL. A piece
        // made of two materials counts under both, so these add up to more than
        // the catalogue holds — the note under the panel says so.
        const [materials, facets] = await Promise.all([
            list(API.materials.list, "materials",
                 { fallback: "Erro ao carregar os materiais." }),
            request(API.products.facets, { fallback: "Erro ao contar as peças." }),
        ]);
        const pieces = new Map(
            (facets.materials ?? []).map((row) => [row.id, row.count])
        );

        rows.innerHTML = materials.length
            ? `<ul class="list-group list-group-flush">${materials
                  .map((m) => `
                    <li class="list-group-item px-0 d-flex justify-content-between align-items-center gap-2">
                      <span data-material-name="${m.id}">${escapeHtml(m.name)}</span>
                      <span class="d-flex align-items-center gap-2">
                      ${pieces.get(m.id)
                          ? `<span class="data text-body-secondary">${pieces.get(m.id)}</span>`
                          : `<span class="badge rounded-pill chip is-quiet">Nenhuma peça</span>`}
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
                      </span>
                    </li>`)
                  .join("")}</ul>`
            : `<p class="text-body-secondary fs-7">Ainda não há materiais.</p>`;

        const spare = materials.filter((m) => !pieces.get(m.id)).length;
        count.textContent = spare
            ? `${materials.length} · ${spare} sem peças`
            : String(materials.length);
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
                text: "As peças feitas dele deixam de o ter. As que também sejam "
                    + "feitas de outro material ficam com esse.",
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
