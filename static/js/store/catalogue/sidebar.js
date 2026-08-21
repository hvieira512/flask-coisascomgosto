import { StoreFilters } from "../filters.js";
import { escapeHtml } from "../../core/html.js";
import { list } from "../../core/api.js";

/**
 * The filter sidebar: one group per facet, each entry a checkbox with a count.
 *
 * There is no Colecção group. The rail of covers above the grid is how a
 * collection is chosen, and a checkbox list beside it was the same question asked
 * twice.
 */

/**
 * One entry: a checkbox, the name, and how many pieces are behind it. The box
 * is what says these are cumulative — before it, a second click looked like
 * it had undone the first.
 */
function renderEntry(group, item, counts) {
    const count = counts.get(item.id) ?? 0;
    // Kept visible but not clickable: it is part of the workshop's vocabulary,
    // and ticking it could only ever empty the grid.
    const empty = count === 0;

    return `
      <li class="nav-item">
        <a class="nav-link filter-entry${empty ? " is-empty" : ""}"
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

/** Fill one group from the endpoint named on it. */
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

    // Cache names so badges can render before the sidebar is consulted.
    items.forEach((item) => StoreFilters.registerLabel(filterGroup, item.id, item.name));
}

/**
 * Fills every group and wires the clicks. `facets` carries the per-option counts,
 * so entries are rendered with their number rather than patched afterwards.
 *
 * Returns the one thing the page has to call again: ticking the entries that the
 * filter state says are chosen.
 */
export async function mountSidebar(facets) {
    const root = document.getElementById("filter-groups");

    root.addEventListener("click", (event) => {
        const link = event.target.closest("a[data-filter-group]");
        if (!link) return;

        event.preventDefault();
        if (link.classList.contains("is-empty")) return;
        StoreFilters.toggle(
            link.dataset.filterGroup,
            link.dataset.filterValue,
            link.dataset.filterLabel
        );
    });

    await Promise.all(
        [...root.querySelectorAll("[data-filter-group]")].map((group) =>
            loadGroup(group, facets)
        )
    );

    return {
        sync() {
            root.querySelectorAll("a[data-filter-group]").forEach((link) => {
                const { filterGroup, filterValue } = link.dataset;
                const on = StoreFilters.isSelected(filterGroup, filterValue);
                link.classList.toggle("is-active", on);
                link.setAttribute("aria-pressed", String(on));
            });
        },
    };
}
