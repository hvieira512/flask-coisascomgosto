import { API, list, request } from "../../core/api.js";
import { Notify } from "../../core/notify.js";
import { byCollection } from "../counts.js";
import { confirmDialog } from "../../core/modal.js";
import { escapeHtml } from "../../core/html.js";
import { openCollectionForm } from "./form.js";

/**
 * Colecções.
 *
 * A collection is what the owners say people ask for first, so the catalogue
 * offers them as photographs. This page is where those photographs are chosen —
 * the form that chooses them is form.js.
 */

let collections = [];
let colorSets = [];
let pieceCounts = new Map();

const findCollection = (id) =>
    collections.find((collection) => collection.id === Number(id)) ?? null;

function collectionRow(collection, pieces) {
    return `
      <tr data-collection-id="${collection.id}">
        <td>
          ${collection.image_url
              ? `<img class="dash-thumb" src="${escapeHtml(collection.image_url)}"
                      alt="Capa de ${escapeHtml(collection.name)}">`
              : `<span class="badge rounded-pill chip is-attention">Sem capa</span>`}
        </td>
        <td><p class="fw-medium mb-0">${escapeHtml(collection.name)}</p></td>
        <td class="fs-7 text-body-secondary">${escapeHtml(collection.description ?? "—")}</td>
        <td>
          ${pieces
              ? `<span class="data text-body-secondary">${pieces} ${pieces === 1 ? "peça" : "peças"}</span>`
              : `<span class="badge rounded-pill chip is-quiet">Sem peças</span>`}
        </td>
        <td class="dash-col-actions">
          <span class="dash-row-actions d-flex gap-1">
            <button class="btn btn-sm btn-ghost" data-collection-action="edit"
                    data-collection-id="${collection.id}" title="Editar"
                    aria-label="Editar ${escapeHtml(collection.name)}">
              <span class="icon"><i class="fa-solid fa-pencil"></i></span>
            </button>
            <button class="btn btn-sm btn-ghost text-danger"
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
        list(API.collections.list, "collections",
             { fallback: "Erro ao carregar as colecções." }),
        byCollection(),
        list(API.colorSets.list, "color_sets",
             { fallback: "Erro ao carregar os conjuntos de cores." }),
    ]);
    pieceCounts = counts;
    collections = all;
    colorSets = sets;

    document.getElementById("collection-rows").innerHTML = all.length
        ? all.map((c) => collectionRow(c, counts.get(c.id) ?? 0)).join("")
        : `<tr><td colspan="5" class="text-center text-body-secondary py-5">
             Ainda não há colecções.</td></tr>`;

    document.getElementById("collection-count").textContent =
        `${all.length} ${all.length === 1 ? "colecção" : "colecções"}`;
}

const editing = (collection) =>
    openCollectionForm({
        modalId: "editCollectionModal",
        collection,
        colorSets,
        after: loadCollections,
    });

function openDelete(id) {
    const collection = findCollection(id);
    if (!collection) return;

    const pieces = pieceCounts.get(collection.id) ?? 0;

    // Nothing is lost with the collection: its pieces and colour sets stay,
    // simply unowned. Saying so is what stops the owners fearing the button.
    const detail = pieces
        ? `<p class="text-body-secondary fs-7 mt-2">
             ${pieces} ${pieces === 1 ? "peça deixa" : "peças deixam"} de pertencer a
             uma colecção. ${pieces === 1 ? "A peça" : "As peças"} e as fotografias
             mantêm-se.
           </p>`
        : "";

    confirmDialog({
        id: "deleteCollectionModal",
        body: `<p>Apagar <strong>${escapeHtml(collection.name)}</strong>?</p>${detail}`,
        onConfirm: () => request(API.collections.delete(id), { method: "DELETE" }),
        success: "Colecção apagada.",
        after: loadCollections,
    });
}

document.getElementById("collection-rows").addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-collection-action]");
    if (trigger) {
        const { collectionAction: action, collectionId: id } = trigger.dataset;

        if (action === "edit") editing(findCollection(id));
        if (action === "delete") openDelete(id);
        return;
    }

    const row = event.target.closest("tr[data-collection-id]");
    if (row) editing(findCollection(row.dataset.collectionId));
});

document.getElementById("new-collection").addEventListener("click", () =>
    openCollectionForm({
        modalId: "newCollectionModal",
        colorSets,
        after: loadCollections,
    })
);

loadCollections().catch((error) => Notify.error(error.message));
