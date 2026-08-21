import { API, list } from "../../core/api.js";
import { ProductPlaceholder } from "../placeholder.js";
import { StoreFilters } from "../filters.js";
import { Track } from "../track.js";
import { escapeHtml } from "../../core/html.js";

/**
 * The collections as photographs, above the grid.
 *
 * It drives the same collection_id filter the sidebar checkboxes drive, rather
 * than a mode of its own: the badge, the sidebar and the URL then all follow from
 * one piece of state, and Limpar clears the rail too.
 *
 * `set` rather than `toggle` because the rail asks a different question from the
 * sidebar. The checkboxes accumulate; a wall of covers reads as "pick one", so
 * picking one replaces whatever was chosen, and picking the chosen one again goes
 * back to everything.
 */
export async function mountRail(facets) {
    const rail = document.getElementById("collection-rail");
    const strip = document.getElementById("collection-strip");

    // Labels are registered here so a badge can say "Colecção: Filigrana" rather
    // than "#1" — this is the only request that carries the names.
    const collections = await list(API.collections.list, "collections", { orEmpty: true });
    collections.forEach((collection) =>
        StoreFilters.registerLabel("collection_id", collection.id, collection.name)
    );

    // The colour sets behind each collection, which tint a cover for a collection
    // that has no photograph yet.
    const sets = await list(API.colorSets.list, "color_sets", { orEmpty: true });
    const setsByCollection = sets.reduce((map, set) => {
        if (!set.collection) return map;
        const current = map.get(set.collection.id) ?? [];
        return map.set(set.collection.id, [...current, set]);
    }, new Map());

    /** Its cover, or the same no-photograph tile the grid uses, tinted in the
     *  collection's own colours rather than a neutral grey. */
    function cover(collection) {
        if (collection.image_url) {
            return `<img src="${escapeHtml(collection.image_url)}"
                         alt="${escapeHtml(collection.name)}" loading="lazy">`;
        }
        return ProductPlaceholder.markup(
            { name: collection.name, type: { icon: "fa-layer-group" } },
            "",
            (setsByCollection.get(collection.id) ?? [])[0] ?? null
        );
    }

    const card = ({ id, name, detail, active, art }) => `
      <li>
        <button type="button" class="collection-card${active ? " is-active" : ""}"
                data-collection-id="${id}" aria-pressed="${active}">
          <span class="collection-cover">${art}</span>
          <span class="collection-card-name">${escapeHtml(name)}</span>
          <span class="collection-card-detail">${escapeHtml(detail)}</span>
        </button>
      </li>`;

    strip?.addEventListener("click", (event) => {
        const chosen = event.target.closest("[data-collection-id]");
        if (!chosen) return;

        const { collectionId: id } = chosen.dataset;
        if (!id) {
            StoreFilters.set("collection_id", null);
            return;
        }

        const already = StoreFilters.isSelected("collection_id", id);
        const name = collections.find((c) => String(c.id) === id)?.name;
        StoreFilters.set("collection_id", already ? null : id, name);

        // The rail is the only way to filter by collection, so this is the most
        // used filter on the page. Only on the way on, like the sidebar's.
        if (!already && name) Track.filter("Colecção", name);
    });

    return {
        render() {
            if (!rail || !strip) return;

            const counts = facets.collections ?? new Map();
            // A collection with nothing behind it is a dead end. A single one still
            // gets a rail, though: with no Colecção group in the sidebar this is the
            // only way to filter by collection at all, and hiding it would remove
            // the filter rather than tidy it away.
            const offered = collections.filter((c) => (counts.get(c.id) ?? 0) > 0);
            rail.hidden = offered.length === 0;
            if (rail.hidden) return;

            const chosen = StoreFilters.get("collection_id");
            strip.innerHTML = [
                card({
                    id: "",
                    name: "Ver tudo",
                    detail: "Todas as peças",
                    active: !chosen || chosen.length === 0,
                    art: `<span class="collection-cover-all disc"><i class="fa-solid fa-grip"></i></span>`,
                }),
                ...offered.map((collection) => {
                    const pieces = counts.get(collection.id) ?? 0;
                    return card({
                        id: collection.id,
                        name: collection.name,
                        detail: `${pieces} ${pieces === 1 ? "peça" : "peças"}`,
                        active: StoreFilters.isSelected("collection_id", collection.id),
                        art: cover(collection),
                    });
                }),
            ].join("");
        },
    };
}
