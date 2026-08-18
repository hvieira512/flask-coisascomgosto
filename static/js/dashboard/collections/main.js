import { escapeHtml } from "../../core/html.js";
import { confirmDialog, formDialog, modal } from "../../core/modal.js";
import { Notify } from "../../core/notify.js";
import {
    countByCollection, createCollection, deleteCollection, listCollections,
    removeCover, updateCollection, uploadCover,
} from "./api.js";

/**
 * Colecções.
 *
 * A collection is what the owners say people ask for first, so the catalogue
 * offers them as photographs. This page is where those photographs are chosen.
 */

let collections = [];
let pieceCounts = new Map();

const findCollection = (id) =>
    collections.find((collection) => collection.id === Number(id)) ?? null;

function collectionRow(collection) {
    const pieces = pieceCounts.get(collection.id) ?? 0;

    return `
      <tr data-collection-id="${collection.id}">
        <td>
          ${collection.image_url
              ? `<img class="dash-thumb" src="${escapeHtml(collection.image_url)}"
                      alt="Capa de ${escapeHtml(collection.name)}">`
              : `<span class="tag is-rounded chip is-attention">Sem capa</span>`}
        </td>
        <td><p class="has-text-weight-medium">${escapeHtml(collection.name)}</p></td>
        <td class="is-size-7 has-text-grey">${escapeHtml(collection.description ?? "—")}</td>
        <td>
          ${pieces
              ? `<span class="data has-text-grey">${pieces} ${pieces === 1 ? "peça" : "peças"}</span>`
              : `<span class="tag is-rounded chip is-quiet">Sem peças</span>`}
        </td>
        <td class="dash-col-actions">
          <span class="dash-row-actions is-flex is-gap-1">
            <button class="button is-small is-ghost" data-collection-action="edit"
                    data-collection-id="${collection.id}" title="Editar"
                    aria-label="Editar ${escapeHtml(collection.name)}">
              <span class="icon"><i class="fa-solid fa-pencil"></i></span>
            </button>
            <button class="button is-small is-ghost has-text-danger"
                    data-collection-action="delete" data-collection-id="${collection.id}"
                    title="Apagar" aria-label="Apagar ${escapeHtml(collection.name)}">
              <span class="icon"><i class="fa-solid fa-trash"></i></span>
            </button>
          </span>
        </td>
      </tr>`;
}

async function loadCollections() {
    const [all, counts] = await Promise.all([listCollections(), countByCollection()]);
    pieceCounts = counts;
    collections = all;

    document.getElementById("collection-rows").innerHTML = all.length
        ? all.map(collectionRow).join("")
        : `<tr><td colspan="5" class="has-text-centered has-text-grey py-6">
             Ainda não há colecções.</td></tr>`;

    document.getElementById("collection-count").textContent =
        `${all.length} ${all.length === 1 ? "colecção" : "colecções"}`;
}

function collectionForm(collection = null) {
    return `
    <form id="collection-form" data-collection-id="${collection?.id ?? ""}">
      <div class="field">
        <label class="label is-small" for="cof-name">Nome</label>
        <input class="input" id="cof-name" name="name" required
               value="${escapeHtml(collection?.name ?? "")}" placeholder="Filigrana">
      </div>

      <div class="field">
        <label class="label is-small" for="cof-description">Descrição</label>
        <textarea class="textarea" id="cof-description" name="description" rows="2"
                  placeholder="O que reúne esta colecção."
                  >${escapeHtml(collection?.description ?? "")}</textarea>
      </div>

      <div class="field mb-0">
        <label class="label is-small">Capa</label>
        <div class="is-flex is-align-items-center is-gap-1 mb-2" id="cof-current">
          ${collection?.image_url
              ? `<img class="dash-thumb" src="${escapeHtml(collection.image_url)}" alt="">
                 <button type="button" class="button is-small is-ghost has-text-danger"
                         id="cof-remove">Remover capa</button>`
              : `<span class="has-text-grey is-size-7">Sem capa.</span>`}
        </div>
        <div class="file is-small has-name">
          <label class="file-label">
            <input class="file-input" type="file" id="cof-file"
                   accept="image/jpeg,image/png,image/webp">
            <span class="file-cta">
              <span class="file-icon"><i class="fa-solid fa-upload"></i></span>
              <span class="file-label">Escolher fotografia</span>
            </span>
            <span class="file-name" id="cof-file-name">Nenhum ficheiro</span>
          </label>
        </div>
        <p class="help">jpg, png ou webp, até 5 MB. Substitui a capa actual.</p>
      </div>
    </form>`;
}

/** The picked filename, and the button that clears an existing cover. */
function wireCoverField(modalId, collection, after) {
    const root = modal(modalId);
    const picker = root.querySelector("#cof-file");

    picker.onchange = () => {
        root.querySelector("#cof-file-name").textContent =
            picker.files[0]?.name ?? "Nenhum ficheiro";
    };

    const remove = root.querySelector("#cof-remove");
    if (remove) {
        remove.onclick = async () => {
            try {
                await removeCover(collection.id);
                Notify.success("Capa removida.");
                root.querySelector("#cof-current").innerHTML =
                    `<span class="has-text-grey is-size-7">Sem capa.</span>`;
                await after();
            } catch (error) {
                Notify.error(error.message);
            }
        };
    }
}

/** The API answers a duplicate in English; the owners read Portuguese. */
const nameTaken = (error) =>
    error.status === 409 ? "Já existe uma colecção com esse nome." : error.message;

function openForm({ modalId, collection = null }) {
    formDialog({
        id: modalId,
        body: collectionForm(collection),
        submitLabel: collection ? "Guardar alterações" : "Criar colecção",
        afterRender: () => wireCoverField(modalId, collection, loadCollections),
        onSubmit: async (dialog) => {
            const form = dialog.querySelector("#collection-form");
            const value = (name) => form.querySelector(`[name="${name}"]`).value.trim();
            if (!value("name")) throw new Error("O nome é obrigatório.");

            const payload = { name: value("name") };
            if (value("description")) payload.description = value("description");
            // Carried through explicitly: a PUT replaces the row, so leaving it
            // out would clear a cover the owner never touched.
            if (collection?.image_url) payload.image_url = collection.image_url;

            let saved;
            try {
                saved = collection
                    ? await updateCollection(collection.id, payload)
                    : await createCollection(payload);
            } catch (error) {
                throw new Error(nameTaken(error));
            }

            // The cover needs an id, so it follows the save rather than riding
            // along with it.
            const file = dialog.querySelector("#cof-file").files[0];
            if (file) await uploadCover(saved.id, file);

            return saved;
        },
        success: collection ? "Colecção actualizada." : "Colecção criada.",
        after: loadCollections,
    });
}

function openDelete(id) {
    const collection = findCollection(id);
    if (!collection) return;

    const pieces = pieceCounts.get(collection.id) ?? 0;

    // Nothing is lost with the collection: its pieces and colour sets stay,
    // simply unowned. Saying so is what stops the owners fearing the button.
    const detail = pieces
        ? `<p class="has-text-grey is-size-7 mt-2">
             ${pieces} ${pieces === 1 ? "peça deixa" : "peças deixam"} de pertencer a
             uma colecção. ${pieces === 1 ? "A peça" : "As peças"} e as fotografias
             mantêm-se.
           </p>`
        : "";

    confirmDialog({
        id: "deleteCollectionModal",
        body: `<p>Apagar <strong>${escapeHtml(collection.name)}</strong>?</p>${detail}`,
        onConfirm: () => deleteCollection(id),
        success: "Colecção apagada.",
        after: loadCollections,
    });
}

document.getElementById("collection-rows").addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-collection-action]");
    if (trigger) {
        const { collectionAction: action, collectionId: id } = trigger.dataset;

        if (action === "edit") {
            openForm({ modalId: "editCollectionModal", collection: findCollection(id) });
        }
        if (action === "delete") openDelete(id);
        return;
    }

    const row = event.target.closest("tr[data-collection-id]");
    if (row) {
        openForm({
            modalId: "editCollectionModal",
            collection: findCollection(row.dataset.collectionId),
        });
    }
});

document.getElementById("new-collection").addEventListener("click", () =>
    openForm({ modalId: "newCollectionModal" })
);

loadCollections().catch((error) => Notify.error(error.message));
