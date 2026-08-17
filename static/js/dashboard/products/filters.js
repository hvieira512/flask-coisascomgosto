import { reference, typeOptions } from "./reference.js";

/**
 * The filter bar above the product grid.
 *
 * Name, type and collection are query parameters, so the API does the work and
 * the result stays correct however large the catalog grows. Filtering by
 * whether a product has photographs has no endpoint, so it is applied to the
 * fetched page — see hasPhotos in fetch.js.
 */
const state = { q: "", type_id: "", collection_id: "", photos: "" };
let onChange = () => {};

const control = (id) => document.getElementById(id);

/** The query string for the API-backed filters. */
export function query() {
    const params = new URLSearchParams({ limit: "100" });
    if (state.q) params.set("q", state.q);
    if (state.type_id) params.set("type_id", state.type_id);
    if (state.collection_id) params.set("collection_id", state.collection_id);
    return params.toString();
}

/** "none" | "some" | "" — applied after the fetch. */
export const photoFilter = () => state.photos;

export const isFiltered = () => Object.values(state).some(Boolean);

function syncClearButton() {
    control("filter-clear").hidden = !isFiltered();
}

export async function mountFilters(handler) {
    onChange = handler;

    const { types, collections } = await reference();

    control("filter-type").insertAdjacentHTML(
        "beforeend",
        typeOptions(types)
            .map((t) => `<option value="${t.id}">${t.label}</option>`)
            .join("")
    );
    control("filter-collection").insertAdjacentHTML(
        "beforeend",
        collections.map((c) => `<option value="${c.id}">${c.name}</option>`).join("")
    );

    // Typing should not fire a request per keystroke.
    let timer;
    control("filter-q").addEventListener("input", (event) => {
        clearTimeout(timer);
        state.q = event.target.value.trim();
        syncClearButton();
        timer = setTimeout(onChange, 250);
    });

    [["filter-type", "type_id"], ["filter-collection", "collection_id"],
     ["filter-photos", "photos"]].forEach(([id, key]) => {
        control(id).addEventListener("change", (event) => {
            state[key] = event.target.value;
            syncClearButton();
            onChange();
        });
    });

    control("filter-clear").addEventListener("click", () => {
        Object.keys(state).forEach((key) => { state[key] = ""; });
        control("filter-q").value = "";
        ["filter-type", "filter-collection", "filter-photos"].forEach((id) => {
            control(id).value = "";
        });
        syncClearButton();
        onChange();
    });

    applyUrlFilters();
}

/**
 * Lets another page link straight to a filtered catalogue — the panel's "N peças
 * sem fotografia" opens ?fotos=none, and the bar has to show that it did, or the
 * list looks wrong rather than filtered.
 */
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

    syncClearButton();
}
