import { API, request } from "../../core/api.js";
import { ColorSet } from "../../store/color-set.js";
import { Notify } from "../../core/notify.js";
import { PhotoPicker } from "../../core/photo-picker.js";
import { escapeHtml, fieldIcon } from "../../core/html.js";
import { formDialog, modal } from "../../core/modal.js";
import { nameTaken } from "../errors.js";

function markup(collection) {
    return `
    <form id="collection-form" data-collection-id="${collection?.id ?? ""}">
      <div class="row g-3">
        <div class="col-md">
          <div class="mb-3">
            <label class="form-label fs-7" for="cof-name">Nome</label>
            <div class="input-group">
              <input class="form-control" id="cof-name" name="name" required
                     value="${escapeHtml(collection?.name ?? "")}" placeholder="Filigrana">
              ${fieldIcon("fa-solid fa-tag")}
            </div>
          </div>

          <div>
            <label class="form-label fs-7" for="cof-description">Descrição</label>
            <textarea class="form-control" id="cof-description" name="description" rows="6"
                      placeholder="O que reúne esta colecção."
                      >${escapeHtml(collection?.description ?? "")}</textarea>
          </div>
        </div>

        <div class="col-md">
          <label class="form-label fs-7">Capa</label>
          <div id="cof-cover"></div>
          <p class="help mb-0">
            A fotografia que representa a colecção no catálogo. jpg, png ou webp,
            até 5 MB.
          </p>
        </div>
      </div>

      <div class="mt-3">
        <label class="form-label fs-7">Conjuntos de cores</label>
        <div class="d-flex flex-wrap gap-1" id="cof-sets"></div>
        <p class="help mb-0">
          As combinações em que esta colecção se faz. Um conjunto pode estar em
          várias colecções — escolher um aqui não o tira de nenhuma.
        </p>
      </div>
    </form>`;
}

function wireColorSets(modalId, collection, colorSets) {
    const container = modal(modalId).querySelector("#cof-sets");

    const isMine = (set) =>
        Boolean(collection) &&
        (set.collections ?? []).some((c) => c.id === collection.id);

    const rank = (set) => (isMine(set) ? 0 : 1);

    container.innerHTML = [...colorSets]
        .sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name, "pt"))
        .map((set) => {
            const mine = isMine(set);
            const others = (set.collections ?? [])
                .filter((c) => c.id !== collection?.id)
                .map((c) => c.name);
            const title = others.length
                ? `${set.name} — também em ${others.join(", ")}`
                : set.name;
            return `
              <button type="button" class="variant-choice${mine ? " is-active" : ""}"
                      data-color-set-id="${set.id}" aria-pressed="${mine}"
                      title="${escapeHtml(title)}">
                ${ColorSet.badge(set)}
              </button>`;
        })
        .join("");

    container.onclick = (event) => {
        const chip = event.target.closest(".variant-choice");
        if (!chip) return;

        const on = chip.getAttribute("aria-pressed") === "true";
        chip.setAttribute("aria-pressed", String(!on));
        chip.classList.toggle("is-active", !on);
    };

    return () =>
        [...container.querySelectorAll('.variant-choice[aria-pressed="true"]')]
            .map((chip) => Number(chip.dataset.colorSetId));
}

function wireCover(modalId, collection, after) {
    return PhotoPicker.mount(modal(modalId).querySelector("#cof-cover"), {
        initial: collection?.image_url
            ? [{ id: collection.id, url: collection.image_url }]
            : [],
        onRemoveStored: async () => {
            await request(API.collections.cover(collection.id), {
                method: "DELETE",
                fallback: "Não foi possível remover a capa.",
            });
            Notify.success("Capa removida.");
            await after();
        },
    });
}

export function openCollectionForm({ modalId, collection = null, colorSets, after }) {
    let chosenSets;
    let cover;

    formDialog({
        id: modalId,
        body: markup(collection),
        submitLabel: collection ? "Guardar alterações" : "Criar colecção",
        afterRender: () => {
            chosenSets = wireColorSets(modalId, collection, colorSets);
            cover = wireCover(modalId, collection, after);
        },
        onSubmit: async (dialog) => {
            const form = dialog.querySelector("#collection-form");
            const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();

            if (!value("name")) throw new Error("O nome é obrigatório.");

            const payload = { name: value("name") };
            if (value("description")) payload.description = value("description");
            if (collection?.image_url) payload.image_url = collection.image_url;

            let saved;
            try {
                saved = await request(
                    collection ? API.collections.update(collection.id)
                               : API.collections.create,
                    { method: collection ? "PUT" : "POST", body: payload }
                );
            } catch (error) {
                throw new Error(nameTaken(error, "uma colecção"));
            }

            await request(API.collections.colorSets(saved.id), {
                method: "PUT",
                body: { color_set_ids: chosenSets() },
                fallback: "Não foi possível guardar os conjuntos de cores.",
            });

            const [file] = cover.files();
            if (file) {
                const form_ = new FormData();
                form_.append("file", file);
                await request(API.collections.cover(saved.id), {
                    method: "POST",
                    body: form_,
                    fallback: "Não foi possível guardar a capa.",
                });
            }

            return saved;
        },
        success: collection ? "Colecção actualizada." : "Colecção criada.",
        after,
    });
}
