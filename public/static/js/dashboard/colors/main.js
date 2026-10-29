import { API, list, request } from "../../core/api.js";
import { Notify } from "../../core/notify.js";
import { escapeHtml } from "../../core/html.js";
import { colorList, openColorForm, openDeleteColor } from "./palette.js";
import { nameTaken } from "../errors.js";
import { openDeleteSet, openSetForm, setRow } from "./sets.js";
import { submitting } from "../../core/modal.js";

let sets = [];
let colors = [];
let collections = [];

const filters = { q: "", collection_id: "", pieces: "" };

const findSet = (id) => sets.find((s) => s.id === Number(id)) ?? null;
const findColor = (id) => colors.find((c) => c.id === Number(id)) ?? null;
const control = (id) => document.getElementById(id);

// Every set is already in memory, so the filters narrow the list here.
function matches(set) {
    if (filters.q && !set.name.toLowerCase().includes(filters.q.toLowerCase())) return false;
    if (filters.collection_id
        && !(set.collections ?? []).some((c) => c.id === Number(filters.collection_id))) return false;
    if (filters.pieces === "none" && set.pieces > 0) return false;
    if (filters.pieces === "some" && set.pieces === 0) return false;
    return true;
}

function renderSets() {
    const filtered = Object.values(filters).some(Boolean);
    const shown = filtered ? sets.filter(matches) : sets;
    const plural = (n) => `${n} ${n === 1 ? "conjunto" : "conjuntos"}`;

    control("set-rows").innerHTML = shown.length
        ? shown.map((set) => setRow(set, set.pieces)).join("")
        : `<tr><td colspan="5" class="text-center text-body-secondary py-5">
             ${filtered ? "Nenhum conjunto corresponde aos filtros."
                        : "Ainda não há conjuntos. Cada peça é oferecida num deles."}</td></tr>`;

    control("set-count").textContent = filtered
        ? `${shown.length} de ${plural(sets.length)}`
        : plural(sets.length);
    control("set-filter-clear").hidden = !filtered;
}

async function loadSets() {
    sets = await list(API.colorSets.list, "color_sets",
                      { fallback: "Erro ao carregar os conjuntos." });
    renderSets();
}

let searchTimer;
control("set-filter-q").addEventListener("input", (event) => {
    clearTimeout(searchTimer);
    filters.q = event.target.value.trim();
    searchTimer = setTimeout(renderSets, 150);
});

[["set-filter-collection", "collection_id"], ["set-filter-pieces", "pieces"]].forEach(([id, key]) => {
    control(id).addEventListener("change", (event) => {
        filters[key] = event.target.value;
        renderSets();
    });
});

control("set-filter-clear").addEventListener("click", () => {
    Object.keys(filters).forEach((key) => { filters[key] = ""; });
    ["set-filter-q", "set-filter-collection", "set-filter-pieces"].forEach((id) => {
        control(id).value = "";
    });
    renderSets();
});

async function loadColors() {
    colors = await list(API.colors.list, "colors",
                        { fallback: "Erro ao carregar as cores." });

    document.getElementById("color-rows").innerHTML = colorList(colors);
    document.getElementById("color-count").textContent = String(colors.length);
}

const reloadBoth = async () => { await loadColors(); await loadSets(); };

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
            if (set) openDeleteSet({ set, pieces: set.pieces, after: loadSets });
        }
        return;
    }

    const row = event.target.closest("tr[data-set-id]");
    if (row) editing(findSet(row.dataset.setId));
});

document.getElementById("new-set").addEventListener("click", () =>
    openSetForm({ modalId: "newSetModal", colors, collections, after: loadSets })
);

loadColors()
    .then(async () => {
        collections = await list(API.collections.list, "collections", { orEmpty: true });
        control("set-filter-collection").insertAdjacentHTML("beforeend",
            collections.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join(""));
    })
    .then(loadSets)
    .catch((error) => Notify.error(error.message));
