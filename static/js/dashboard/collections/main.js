import { PhotoPicker } from "../../core/photo-picker.js";
import { escapeHtml } from "../../core/html.js";
import { confirmDialog, formDialog, modal } from "../../core/modal.js";
import { Notify } from "../../core/notify.js";
import { ColorSet } from "../../store/color-set.js";
import {
    countByCollection, createCollection, deleteCollection, listCollections,
    listColorSets, removeCover, setColorSets, updateCollection, uploadCover,
} from "./api.js";

/**
 * Colecções.
 *
 * A collection is what the owners say people ask for first, so the catalogue
 * offers them as photographs. This page is where those photographs are chosen.
 */

let collections = [];
let colorSets = [];
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
    // The colour sets come along because the form offers all of them, and because
    // which collection each belongs to changes when one is saved.
    const [all, counts, sets] = await Promise.all([
        listCollections(), countByCollection(), listColorSets(),
    ]);
    pieceCounts = counts;
    collections = all;
    colorSets = sets;

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
      <!-- What it is on the left, what it looks like on the right. Bulma's columns
           stack below 769px, so on a phone the cover simply follows the fields. -->
      <div class="columns is-variable is-4 mb-0">
        <div class="column">
          <div class="field">
            <label class="label is-small" for="cof-name">Nome</label>
            <input class="input" id="cof-name" name="name" required
                   value="${escapeHtml(collection?.name ?? "")}" placeholder="Filigrana">
          </div>

          <div class="field mb-0">
            <label class="label is-small" for="cof-description">Descrição</label>
            <!-- Taller than the two lines it needs, so the column of fields reaches
                 roughly the depth of the cover beside it. -->
            <textarea class="textarea" id="cof-description" name="description" rows="6"
                      placeholder="O que reúne esta colecção."
                      >${escapeHtml(collection?.description ?? "")}</textarea>
          </div>
        </div>

        <div class="column">
          <div class="field mb-0">
            <label class="label is-small">Capa</label>
            <div id="cof-cover"></div>
            <p class="help">
              A fotografia que representa a colecção no catálogo. jpg, png ou webp,
              até 5 MB.
            </p>
          </div>
        </div>
      </div>

      <!-- Across the full width, under both columns: nine badges need the room, and
           they are about the collection as a whole rather than about either side. -->
      <div class="field mt-4 mb-0">
        <label class="label is-small">Conjuntos de cores</label>
        <div class="tags" id="cof-sets"></div>
        <p class="help">
          As combinações em que esta colecção se faz. Cada conjunto pertence a uma só
          colecção, por isso escolher um que esteja noutra passa-o para esta.
        </p>
      </div>
    </form>`;
}

/**
 * The colour sets, as the badges the storefront draws, with the ones already in this
 * collection chosen. Same chip and same ring as the create wizard's colour step, so
 * "chosen" looks the same wherever it is asked.
 *
 * Sorted so the collection's own come first, then the unowned, then the ones that
 * would have to be taken from another collection — whose name is in the title, since
 * choosing one of those moves it.
 */
function wireColorSetField(modalId, collection) {
    const root = modal(modalId);
    const container = root.querySelector("#cof-sets");

    const rank = (set) => {
        if (set.collection?.id === collection?.id) return 0;
        return set.collection ? 2 : 1;
    };

    container.innerHTML = [...colorSets]
        .sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name, "pt"))
        .map((set) => {
            const mine = collection && set.collection?.id === collection.id;
            const elsewhere = set.collection && !mine ? set.collection.name : null;
            return `
              <button type="button" class="variant-choice${mine ? " is-active" : ""}"
                      data-color-set-id="${set.id}" aria-pressed="${Boolean(mine)}"
                      title="${elsewhere ? `Está em ${escapeHtml(elsewhere)}` : escapeHtml(set.name)}">
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

/**
 * The cover slot. One photograph, so one slot: it shows the cover the collection
 * already has, and clearing it removes the cover then and there — the collection
 * exists, unlike a piece being created.
 */
function wireCoverField(modalId, collection, after) {
    const root = modal(modalId);

    return PhotoPicker.mount(root.querySelector("#cof-cover"), {
        initial: collection?.image_url
            ? [{ id: collection.id, url: collection.image_url }]
            : [],
        onRemoveStored: async () => {
            await removeCover(collection.id);
            Notify.success("Capa removida.");
            await after();
        },
    });
}

/** The API answers a duplicate in English; the owners read Portuguese. */
const nameTaken = (error) =>
    error.status === 409 ? "Já existe uma colecção com esse nome." : error.message;

function openForm({ modalId, collection = null }) {
    let cover = { files: () => [] };
    let chosenSets = () => [];

    formDialog({
        id: modalId,
        body: collectionForm(collection),
        submitLabel: collection ? "Guardar alterações" : "Criar colecção",
        afterRender: () => {
            cover = wireCoverField(modalId, collection, loadCollections);
            chosenSets = wireColorSetField(modalId, collection);
        },
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

            // Both of these need an id, so they follow the save rather than riding
            // along with it.
            await setColorSets(saved.id, chosenSets());

            const [file] = cover.files();
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
