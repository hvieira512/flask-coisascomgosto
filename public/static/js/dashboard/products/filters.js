import { escapeHtml } from "../../core/html.js";
import { reference, typeOptions } from "./reference.js";

const state = { q: "", type_id: "", collection_id: "", photos: "" };
let onChange = () => {};
let mounted = false;

const control = (id) => document.getElementById(id);

// The filters as API parameters. `photos` overrides the photograph filter, so the
// count of pieces without one can be asked under the same other filters.
export function filterParams({ photos = state.photos } = {}) {
    const params = {};
    if (state.q) params.q = state.q;
    if (state.type_id) params.type_id = state.type_id;
    if (state.collection_id) params.collection_id = state.collection_id;
    if (photos) params.has_photos = photos === "some" ? 1 : 0;
    return params;
}

export const photoFilter = () => state.photos;

export const isFiltered = () => Object.values(state).some(Boolean);

function syncClearButton() {
    control("filter-clear").hidden = !isFiltered();
}

export async function mountFilters(handler) {
    onChange = handler;

    // Called again after every save; a second mount appended every option and
    // every listener again, so one change fetched the list several times.
    if (mounted) return;
    mounted = true;

    const { types, collections } = await reference();

    control("filter-type").insertAdjacentHTML(
        "beforeend",
        typeOptions(types)
            .map((t) => `<option value="${t.id}">${escapeHtml(t.label)}</option>`)
            .join("")
    );
    control("filter-collection").insertAdjacentHTML(
        "beforeend",
        collections.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("")
    );

    let timer;
    control("filter-q").addEventListener("input", (event) => {
        clearTimeout(timer);
        state.q = event.target.value.trim();
        syncClearButton();
        timer = setTimeout(() => onChange(1), 250);
    });

    [["filter-type", "type_id"], ["filter-collection", "collection_id"],
     ["filter-photos", "photos"]].forEach(([id, key]) => {
        control(id).addEventListener("change", (event) => {
            state[key] = event.target.value;
            syncClearButton();
            onChange(1);
        });
    });

    control("filter-clear").addEventListener("click", () => {
        Object.keys(state).forEach((key) => { state[key] = ""; });
        control("filter-q").value = "";
        ["filter-type", "filter-collection", "filter-photos"].forEach((id) => {
            control(id).value = "";
        });
        syncClearButton();
        onChange(1);
    });

    applyUrlFilters();
}

function applyUrlFilters() {
    const params = new URLSearchParams(window.location.search);

    const photos = params.get("fotos");
    if (photos === "none" || photos === "some") {
        state.photos = photos;
        control("filter-photos").value = photos;
    }

    const q = params.get("q");
    if (q) {
        state.q = q;
        control("filter-q").value = q;
    }

    const type = params.get("tipo");
    if (type && control("filter-type").querySelector(`option[value="${CSS.escape(type)}"]`)) {
        state.type_id = type;
        control("filter-type").value = type;
    }

    syncClearButton();
}
