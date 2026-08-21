import { API, list } from "../../core/api.js";
import { StoreFilters } from "../filters.js";
import { Track } from "../track.js";
import { escapeHtml } from "../../core/html.js";
import { mountDragRail } from "../drag-rail.js";

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

    // Dragged with the mouse, or walked with the arrows, which appear on hover
    // and only when the rail has somewhere to go. Same behaviour as the fairs.
    const arrows = mountDragRail(strip, {
        prev: rail?.querySelector("[data-rail-prev]"),
        next: rail?.querySelector("[data-rail-next]"),
        item: "li",
    });

    // Labels are registered here so a badge can say "Colecção: Filigrana" rather
    // than "#1" — this is the only request that carries the names.
    const collections = await list(API.collections.list, "collections", { orEmpty: true });
    collections.forEach((collection) =>
        StoreFilters.registerLabel("collection_id", collection.id, collection.name)
    );

    /**
     * Its cover, or its name set in the display serif.
     *
     * Not a grey box with a stack icon in a blue disc, which is what three of
     * the four collections got: the first thing on the page that sells the range
     * was selling an empty database column.
     */
    // d-block on the ratio box as well as .ratio: Bootstrap's rule sets position
    // and width but not display, so as a span it stayed inline and the
    // photograph came out half the tile's width.
    function tile({ id, name, detail, active, photo, empty }) {
        const art = photo
            ? `<img class="object-fit-cover" src="${escapeHtml(photo)}"
                    alt="${escapeHtml(name)}" loading="lazy">`
            : `<span class="d-flex flex-column align-items-center justify-content-center
                           text-center bg-body-secondary border p-3">
                 <span class="collection-card-name font-display fs-5 text-body-secondary">${escapeHtml(name)}</span>
                 <span class="collection-card-detail fs-7 text-uppercase text-body-tertiary">${escapeHtml(detail)}</span>
               </span>`;

        const label = photo
            ? `<span class="position-absolute top-0 start-0 w-100 h-100 tile-scrim"></span>
               <span class="position-absolute bottom-0 start-0 p-3 text-white">
                 <span class="collection-card-name d-block font-display fs-5 lh-sm">${escapeHtml(name)}</span>
                 <span class="collection-card-detail fs-7 text-uppercase opacity-75">${escapeHtml(detail)}</span>
               </span>`
            : "";

        // A collection with nothing in it yet is shown and not offered — the same
        // decision the sidebar already makes for a material with no pieces:
        // it is part of the workshop's vocabulary, and choosing it could only
        // ever empty the grid.
        const state = empty
            ? 'aria-disabled="true" title="Ainda sem peças"'
            : `aria-pressed="${active}" data-collection-id="${id}"`;

        return `
      <li>
        <button type="button" ${state}
                class="collection-card d-block w-100 p-0 border-0 bg-transparent position-relative overflow-hidden${empty ? " is-empty" : ""}">
          <span class="collection-cover ratio d-block" style="--bs-aspect-ratio: 66%">${art}</span>
          ${label}
        </button>
      </li>`;
    }

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
            rail.hidden = collections.length === 0;
            if (rail.hidden) return;

            // Every collection the workshop has, however few pieces are filed
            // under it yet. The rail used to offer only those with pieces, which
            // hid three of the six — and those three are the ones with cover
            // photographs. An empty one is drawn and not offered; see tile().
            strip.innerHTML = collections
                .map((collection) => {
                    const pieces = counts.get(collection.id) ?? 0;
                    return tile({
                        id: collection.id,
                        name: collection.name,
                        photo: collection.image_url,
                        detail: pieces
                            ? `${pieces} ${pieces === 1 ? "peça" : "peças"}`
                            : "ainda sem peças",
                        empty: pieces === 0,
                        active: StoreFilters.isSelected("collection_id", collection.id),
                    });
                })
                .join("");

            arrows?.syncArrows();
        },
    };
}
