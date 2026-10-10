import { API, list } from "../../core/api.js";
import { StoreFilters } from "../filters.js";
import { Track } from "../track.js";
import { escapeHtml } from "../../core/html.js";
import { mountDragRail } from "../drag-rail.js";

export async function mountRail(facets) {
    const rail = document.getElementById("collection-rail");
    const strip = document.getElementById("collection-strip");

    const arrows = mountDragRail(strip, {
        prev: rail?.querySelector("[data-rail-prev]"),
        next: rail?.querySelector("[data-rail-next]"),
        item: "li",
    });

    const collections = await list(API.collections.list, "collections", { orEmpty: true });
    collections.forEach((collection) =>
        StoreFilters.registerLabel("collection_id", collection.id, collection.name)
    );

    function tile({ id, name, detail, active, photo, empty }) {
        const art = photo
            ? `<img class="object-fit-cover" src="${escapeHtml(photo)}"
                    alt="${escapeHtml(name)}" loading="lazy">`
            : `<span class="d-flex flex-column align-items-center justify-content-center
                           text-center bg-body-secondary border p-3">
                 <span class="collection-card-name font-display fs-5 text-body-secondary">${escapeHtml(name)}</span>
                 <span class="collection-card-detail fs-7 text-body-secondary">${escapeHtml(detail)}</span>
               </span>`;

        const label = photo
            ? `<span class="position-absolute top-0 start-0 w-100 h-100 tile-scrim"></span>
               <span class="position-absolute bottom-0 start-0 p-3 text-white">
                 <span class="collection-card-name d-block font-display fs-5 lh-sm">${escapeHtml(name)}</span>
                 <span class="collection-card-detail fs-7 opacity-75">${escapeHtml(detail)}</span>
               </span>`
            : "";

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

        if (!already && name) Track.filter("Colecção", name);
    });

    return {
        render() {
            if (!rail || !strip) return;

            const counts = facets.collections ?? new Map();
            rail.hidden = collections.length === 0;
            if (rail.hidden) return;

            strip.innerHTML = collections
                .map((collection) => {
                    const pieces = counts.get(collection.id) ?? 0;
                    return tile({
                        id: collection.id,
                        name: collection.name,
                        photo: collection.image_url || collection.borrowed_image_url,
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
