import { API, list, request } from "../../core/api.js";
import { Notify } from "../../core/notify.js";
import { byColorSet } from "../counts.js";
import { colorList, openColorForm, openDeleteColor } from "./palette.js";
import { nameTaken } from "../errors.js";
import { openDeleteSet, openSetForm, setRow } from "./sets.js";
import { submitting } from "../../core/modal.js";

/**
 * Cores e conjuntos.
 *
 * Two screens on one page, which is why this file only holds what they share: the
 * three lists, and the fact that a change to either side redraws both. A colour
 * set is built from colours, and a renamed colour has to reappear inside every
 * set that uses it.
 *
 * sets.js draws and edits the conjuntos; palette.js the colours.
 */

let sets = [];
let colors = [];
let collections = [];
let pieceCounts = new Map();

const findSet = (id) => sets.find((s) => s.id === Number(id)) ?? null;
const findColor = (id) => colors.find((c) => c.id === Number(id)) ?? null;

async function loadSets() {
    const [all, counts] = await Promise.all([
        list(API.colorSets.list, "color_sets",
             { fallback: "Erro ao carregar os conjuntos." }),
        byColorSet(),
    ]);
    pieceCounts = counts;
    sets = all;

    document.getElementById("set-rows").innerHTML = all.length
        ? all.map((set) => setRow(set, counts.get(set.id) ?? 0)).join("")
        : `<tr><td colspan="5" class="text-center text-body-secondary py-5">
             Ainda não há conjuntos. Cada peça é oferecida num deles.</td></tr>`;

    document.getElementById("set-count").textContent =
        `${all.length} ${all.length === 1 ? "conjunto" : "conjuntos"}`;
}

async function loadColors() {
    colors = await list(API.colors.list, "colors",
                        { fallback: "Erro ao carregar as cores." });

    document.getElementById("color-rows").innerHTML = colorList(colors);
    document.getElementById("color-count").textContent = String(colors.length);
}

/** A renamed or recoloured colour shows up inside every set that uses it. */
const reloadBoth = async () => { await loadColors(); await loadSets(); };

// ---- Wiring ----

document.getElementById("color-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const nameInput = document.getElementById("color-name");
    const name = nameInput.value.trim();
    if (!name) return;

    return submitting(event.submitter ?? event.target.querySelector("button"), async () => {
        try {
            await request(API.colors.create, {
                method: "POST",
                body: { name, hex: document.getElementById("color-hex").value },
            });
        } catch (error) {
            throw new Error(nameTaken(error, "uma cor"));
        }
        nameInput.value = "";
        Notify.success("Cor adicionada.");
        await loadColors();
    });
});

document.getElementById("color-rows").addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-color-action]");
    if (!trigger) return;

    const color = findColor(trigger.dataset.colorId);
    if (!color) return;

    if (trigger.dataset.colorAction === "edit") {
        openColorForm({ color, after: reloadBoth });
    }
    if (trigger.dataset.colorAction === "delete") {
        openDeleteColor({
            color,
            using: sets.filter((set) => set.colors.some((c) => c.id === color.id)),
            after: reloadBoth,
        });
    }
});

document.getElementById("set-rows").addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-set-action]");
    const editing = (set) =>
        openSetForm({ modalId: "editSetModal", set, colors, collections, after: loadSets });

    if (trigger) {
        const { setAction: action, setId: id } = trigger.dataset;

        if (action === "edit") editing(findSet(id));
        if (action === "delete") {
            const set = findSet(id);
            if (set) openDeleteSet({ set, pieces: pieceCounts.get(set.id) ?? 0, after: loadSets });
        }
        return;
    }

    const row = event.target.closest("tr[data-set-id]");
    if (row) editing(findSet(row.dataset.setId));
});

document.getElementById("new-set").addEventListener("click", () =>
    openSetForm({ modalId: "newSetModal", colors, collections, after: loadSets })
);

// Colours load first: the set form's picker is built from them.
loadColors()
    .then(async () => {
        collections = await list(API.collections.list, "collections", { orEmpty: true });
    })
    .then(loadSets)
    .catch((error) => Notify.error(error.message));
