import { escapeHtml } from "../../core/html.js";

const pieces = (n) => `${n} ${n === 1 ? "peça" : "peças"}`;

// A collection as a door with a photograph, in the grid's own cell. The scrim
// keeps the name legible whatever the photograph; without one it sits on mist.
function tile({ id, name, photo, count }) {
    const art = photo
        ? `<img class="object-fit-cover" src="${escapeHtml(photo)}" alt="" loading="lazy">`
        : `<span class="bg-body-secondary"></span>`;

    return `
      <div class="col">
        <a class="collection-tile d-block position-relative overflow-hidden rounded-3 text-decoration-none text-white"
           href="/products?collection_id=${id}" data-collection-id="${id}" data-collection-name="${escapeHtml(name)}">
          <span class="ratio d-block" style="--bs-aspect-ratio: 75%">${art}</span>
          <span class="position-absolute top-0 start-0 w-100 h-100 tile-scrim"></span>
          <span class="position-absolute bottom-0 start-0 end-0 p-3">
            <span class="collection-tile-name d-block font-display fs-5 lh-sm">${escapeHtml(name)}</span>
            <span class="fs-7 opacity-75">${pieces(count)}</span>
          </span>
        </a>
      </div>`;
}

// The last tile opens everything, which is how a piece filed under no
// collection is reached.
const allTile = (count) => `
      <div class="col">
        <a class="collection-tile d-block position-relative overflow-hidden rounded-3 text-decoration-none text-white bg-dark"
           href="/products?all=1" data-collection-all>
          <span class="ratio d-block" style="--bs-aspect-ratio: 75%"></span>
          <span class="position-absolute bottom-0 start-0 end-0 p-3">
            <span class="collection-tile-name d-block font-display fs-5 lh-sm">Todas as peças</span>
            <span class="fs-7 opacity-75">${pieces(count)}</span>
          </span>
        </a>
      </div>`;

const skeletonTile = `
      <div class="col">
        <span class="ratio d-block rounded-3 placeholder" style="--bs-aspect-ratio: 75%"></span>
      </div>`;

export function mountCollections(onOpen) {
    const root = document.getElementById("collection-grid");

    root.addEventListener("click", (event) => {
        const chosen = event.target.closest("a[data-collection-id], a[data-collection-all]");
        if (!chosen || event.metaKey || event.ctrlKey || event.shiftKey) return;

        event.preventDefault();
        onOpen(chosen.dataset.collectionId ?? null, chosen.dataset.collectionName ?? null);
    });

    return {
        skeleton() {
            root.classList.add("placeholder-glow");
            root.innerHTML = skeletonTile.repeat(6);
        },

        render(collections, counts, total) {
            root.classList.remove("placeholder-glow");
            root.innerHTML = collections
                .filter((collection) => (counts.get(collection.id) ?? 0) > 0)
                .map((collection) => tile({
                    id: collection.id,
                    name: collection.name,
                    photo: collection.image_url || collection.borrowed_image_url,
                    count: counts.get(collection.id),
                }))
                .join("") + (total > 0 ? allTile(total) : "");
        },
    };
}
