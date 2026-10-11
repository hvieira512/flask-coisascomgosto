import { StoreFilters } from "../filters.js";
import { escapeHtml } from "../../core/html.js";
import { list } from "../../core/api.js";
import { Track } from "../track.js";

const FACET_NAMES = {
    type_id: "Tipo",
    material_id: "Material",
};

function renderEntry(group, item, counts) {
    const count = counts.get(item.id) ?? 0;
    const empty = count === 0;

    return `
      <li class="nav-item">
        <a class="nav-link filter-entry${empty ? " is-empty" : ""}"
           role="checkbox" aria-checked="false" tabindex="${empty ? -1 : 0}"
           data-filter-group="${group}" data-filter-value="${item.id}"
           data-filter-label="${escapeHtml(item.name)}"
           ${empty ? 'aria-disabled="true" title="Sem peças"' : ""}>
          <span class="filter-line">
            <span class="filter-box" aria-hidden="true">
              <i class="fa-solid fa-check"></i>
            </span>
            <span class="filter-name">${escapeHtml(item.name)}</span>
            <span class="filter-count">${count}</span>
          </span>
        </a>
      </li>`;
}

async function loadGroup(group, facets) {
    const { filterGroup, endpoint, collectionKey, facet } = group.dataset;

    let items;
    try {
        items = await list(endpoint, collectionKey);
    } catch (error) {
        group.innerHTML =
            '<li><span class="text-body-secondary fs-7">Indisponível</span></li>';
        return;
    }

    const counts = facets[facet] ?? new Map();
    group.innerHTML = items.map((item) => renderEntry(filterGroup, item, counts)).join("");

    items.forEach((item) => StoreFilters.registerLabel(filterGroup, item.id, item.name));
}

export async function mountSidebar(facets) {
    const root = document.getElementById("filter-groups");

    function toggle(entry) {
        if (entry.classList.contains("is-empty")) return;

        const { filterGroup, filterValue, filterLabel } = entry.dataset;
        const turningOn = !StoreFilters.isSelected(filterGroup, filterValue);

        StoreFilters.toggle(filterGroup, filterValue, filterLabel);

        if (turningOn) Track.filter(FACET_NAMES[filterGroup] ?? filterGroup, filterLabel);
    }

    root.addEventListener("click", (event) => {
        const entry = event.target.closest("a[data-filter-group]");
        if (!entry) return;

        event.preventDefault();
        toggle(entry);
    });

    root.addEventListener("keydown", (event) => {
        if (event.key !== " " && event.key !== "Enter") return;

        const entry = event.target.closest("a[data-filter-group]");
        if (!entry) return;

        event.preventDefault();
        toggle(entry);
    });

    await Promise.all(
        [...root.querySelectorAll("[data-filter-group]")].map((group) =>
            loadGroup(group, facets)
        )
    );

    return {
        sync() {
            root.querySelectorAll("a[data-filter-group]").forEach((entry) => {
                const { filterGroup, filterValue } = entry.dataset;
                const on = StoreFilters.isSelected(filterGroup, filterValue);
                entry.classList.toggle("is-active", on);
                entry.setAttribute("aria-checked", String(on));
            });
        },

        // The counts follow the collection that is open. A ticked entry stays
        // live even at zero, or it could never be unticked.
        updateCounts(facets) {
            root.querySelectorAll("a[data-filter-group]").forEach((entry) => {
                const { filterGroup, filterValue } = entry.dataset;
                const facet = entry.closest("[data-facet]")?.dataset.facet;
                const count = facets[facet]?.get(Number(filterValue)) ?? 0;
                const empty = count === 0 && !StoreFilters.isSelected(filterGroup, filterValue);

                entry.querySelector(".filter-count").textContent = count;
                entry.classList.toggle("is-empty", empty);
                entry.tabIndex = empty ? -1 : 0;
                if (empty) {
                    entry.setAttribute("aria-disabled", "true");
                    entry.title = "Sem peças";
                } else {
                    entry.removeAttribute("aria-disabled");
                    entry.removeAttribute("title");
                }
            });
        },
    };
}
