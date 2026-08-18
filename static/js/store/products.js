/**
 * Catalog page: filter sidebar, applied-filter badges and the product grid.
 *
 * The sidebar and the badge row are two renderings of the same StoreFilters
 * state, so selecting an entry in the sidebar and removing its badge are the
 * same operation.
 */

import { ColorSet } from "./color-set.js";
import { ProductPlaceholder } from "./placeholder.js";
import { StoreApi } from "./api.js";
import { StoreFilters } from "./filters.js";
import { escapeHtml } from "../core/html.js";

(function () {
    const grid = document.getElementById("product-grid");
    const emptyNotice = document.getElementById("grid-empty");
    const badgeRow = document.getElementById("active-filters");
    const resultCount = document.getElementById("result-count");
    const clearButton = document.getElementById("clear-filters");
    const searchInput = document.getElementById("filter-search");
    const pagination = document.getElementById("pagination");
    const pageList = document.getElementById("page-list");

    let page = 1;
    let totalPages = 1;
    /** option id -> how many products, per group. Filled once, before the lists. */
    let facets = {};
    /** collection id -> its colour sets, so a collection reads as its colours. */
    let setsByCollection = new Map();

    // ----------------------------------------------------------------
    // Sidebar
    // ----------------------------------------------------------------

    /** Per-option product counts, so an entry can say what it holds. */
    async function loadFacets() {
        try {
            const payload = await StoreApi.get("/api/products/facets");
            facets = Object.fromEntries(
                Object.entries(payload).map(([key, rows]) => [
                    key,
                    new Map(rows.map((row) => [row.id, row.count])),
                ])
            );
        } catch (error) {
            facets = {};
        }
    }

    /** The colour sets behind each collection — a collection is its colours. */
    async function loadColorSets() {
        try {
            const { color_sets: sets } = await StoreApi.get("/api/color-sets/", {
                limit: 100,
            });
            setsByCollection = sets.reduce((map, set) => {
                if (!set.collection) return map;
                const current = map.get(set.collection.id) ?? [];
                return map.set(set.collection.id, [...current, set]);
            }, new Map());
        } catch (error) {
            setsByCollection = new Map();
        }
    }

    /** Fill one sidebar group from its API endpoint. */
    async function loadGroup(list) {
        const { filterGroup, endpoint, collectionKey, facet, withColorSets } =
            list.dataset;

        let payload;
        try {
            payload = await StoreApi.get(endpoint, { limit: 100 });
        } catch (error) {
            list.innerHTML = '<li><span class="has-text-grey is-size-7">Indisponível</span></li>';
            return;
        }

        const items = payload[collectionKey] || [];
        const counts = facets[facet] ?? new Map();
        list.innerHTML = items
            .map((item) => renderEntry(filterGroup, item, counts, withColorSets))
            .join("");

        // Cache names so badges can render before the sidebar is consulted.
        items.forEach((item) =>
            StoreFilters.registerLabel(filterGroup, item.id, item.name)
        );
    }

    /**
     * One entry: a checkbox, the name, and how many pieces are behind it. The box
     * is what says these are cumulative — before it, a second click looked like
     * it had undone the first.
     */
    function renderEntry(group, item, counts, withColorSets) {
        const count = counts.get(item.id) ?? 0;
        const sets = withColorSets ? setsByCollection.get(item.id) ?? [] : [];
        const badges = sets.map((set) => ColorSet.badge(set)).join("");
        // Kept visible but not clickable: it is part of the workshop's
        // vocabulary, and ticking it could only ever empty the grid.
        const empty = count === 0;

        return `
          <li>
            <a class="filter-entry${empty ? " is-empty" : ""}"
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
              ${badges ? `<span class="filter-sets swatch-row">${badges}</span>` : ""}
            </a>
          </li>`;
    }

    /** Tick whichever sidebar entries are selected. */
    function syncSidebar() {
        document.querySelectorAll("#filter-groups a[data-filter-group]").forEach((link) => {
            const { filterGroup, filterValue } = link.dataset;
            const on = StoreFilters.isSelected(filterGroup, filterValue);
            link.classList.toggle("is-active", on);
            link.setAttribute("aria-pressed", String(on));
        });
    }

    document.getElementById("filter-groups").addEventListener("click", (event) => {
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

    // ----------------------------------------------------------------
    // Applied-filter badges
    // ----------------------------------------------------------------

    /**
     * One Bulma tag per selected value, shaped "Group: Value ×" — three ticked
     * types are three tags, each removable on its own.
     */
    function renderBadges() {
        const chosen = StoreFilters.selections();
        badgeRow.hidden = chosen.length === 0;
        clearButton.hidden = chosen.length === 0;

        badgeRow.innerHTML = chosen
            .map(({ group, value }) => {
                const groupLabel = StoreFilters.GROUPS[group].label;
                const valueLabel = StoreFilters.labelFor(group, value);
                return `
                  <span class="tag is-dark is-medium filter-badge"
                        data-remove-filter="${group}" data-remove-value="${escapeHtml(value)}"
                        role="button" tabindex="0"
                        title="Remover ${escapeHtml(valueLabel)}">
                    ${escapeHtml(groupLabel)}: ${escapeHtml(valueLabel)}
                    <button class="delete is-small" aria-label="Remover ${escapeHtml(valueLabel)}"></button>
                  </span>`;
            })
            .join("");
    }

    function removeBadge(badge) {
        const { removeFilter: group, removeValue: value } = badge.dataset;
        StoreFilters.clear(group, value ?? null);
        if (group === "q") searchInput.value = "";
    }

    badgeRow.addEventListener("click", (event) => {
        const badge = event.target.closest("[data-remove-filter]");
        if (badge) removeBadge(badge);
    });

    // Keyboard parity: the badge is focusable, so Enter/Space must remove it too.
    badgeRow.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;

        const badge = event.target.closest("[data-remove-filter]");
        if (!badge) return;

        event.preventDefault();
        removeBadge(badge);
    });

    clearButton.addEventListener("click", () => {
        StoreFilters.clearAll();
        searchInput.value = "";
    });

    // ----------------------------------------------------------------
    // Search box
    // ----------------------------------------------------------------

    let searchTimer;
    searchInput.addEventListener("input", (event) => {
        clearTimeout(searchTimer);
        const value = event.target.value.trim();
        searchTimer = setTimeout(() => StoreFilters.set("q", value || null), 250);
    });

    // ----------------------------------------------------------------
    // Grid
    // ----------------------------------------------------------------

    /** Two rows of two. A fifth colour set added a third row to one card and
     *  left it taller than its neighbours; the rest are on the product page. */
    const MAX_BADGES = 4;

    function renderColorSets(product) {
        const sets = product.variants.map((variant) => variant.color_set).filter(Boolean);
        if (!sets.length) return "";

        const overflows = sets.length > MAX_BADGES;
        const visible = overflows ? MAX_BADGES - 1 : sets.length;
        const cells = sets.slice(0, visible).map(ColorSet.badge);

        if (overflows) {
            const rest = sets.length - visible;
            cells.push(
                `<span class="tag is-rounded color-set-more">+${rest} ${
                    rest === 1 ? "cor" : "cores"
                }</span>`
            );
        }

        return `<div class="swatch-row">${cells.join("")}</div>`;
    }

    function renderCard(product) {
        const image = product.primary_image;
        const media = image
            ? `<img src="${escapeHtml(image.url)}" alt="${escapeHtml(image.alt || product.name)}" loading="lazy">`
            : ProductPlaceholder.markup(product);

        const subtitle = [product.type?.name, product.collection?.name]
            .filter(Boolean)
            .map(escapeHtml)
            .join(" · ");

        return `
          <div class="cell">
            <a class="card product-card" href="/products/${product.id}">
              <div class="card-image">${media}</div>
              <div class="card-content">
                <p class="title is-6 mb-1">${escapeHtml(product.name)}</p>
                ${subtitle ? `<p class="is-size-7 has-text-grey">${subtitle}</p>` : ""}
                ${renderColorSets(product)}
              </div>
            </a>
          </div>`;
    }

    async function loadProducts() {
        const params = {
            ...StoreFilters.active(),
            page,
            limit: 9,
            photographed_first: 1,
        };

        let payload;
        try {
            payload = await StoreApi.products(params);
        } catch (error) {
            grid.innerHTML = "";
            emptyNotice.hidden = false;
            emptyNotice.textContent = "Não foi possível carregar os produtos.";
            return;
        }

        const products = payload.products || [];
        grid.innerHTML = products.map(renderCard).join("");

        emptyNotice.hidden = products.length > 0;
        emptyNotice.textContent = "Nenhum produto corresponde aos filtros escolhidos.";

        const { total, pages } = payload.pagination;
        totalPages = pages || 1;
        resultCount.textContent = total === 1 ? "1 produto" : `${total} produtos`;

        renderPagination();
    }

    // ----------------------------------------------------------------
    // Pagination
    // ----------------------------------------------------------------

    /** Above this many pages the middle is elided rather than listed. */
    const MAX_PAGE_BUTTONS = 7;

    /**
     * The page numbers to draw, with null standing for an ellipsis. Always keeps
     * the first, the last and the current page's neighbours, so the row never
     * changes width as you walk through it.
     */
    function pageWindow() {
        if (totalPages <= MAX_PAGE_BUTTONS) {
            return Array.from({ length: totalPages }, (_, i) => i + 1);
        }

        const around = [page - 1, page, page + 1].filter(
            (n) => n > 1 && n < totalPages
        );
        const numbers = [1, ...around, totalPages];

        return numbers.flatMap((n, i) =>
            i > 0 && n - numbers[i - 1] > 1 ? [null, n] : [n]
        );
    }

    const arrow = (icon, label, target, disabled) => `
      <li>
        <button class="pagination-link" type="button" data-page="${target}"
                aria-label="${label}"${disabled ? " disabled" : ""}>
          <span class="icon is-small"><i class="fa-solid ${icon}"></i></span>
        </button>
      </li>`;

    function renderPagination() {
        pagination.hidden = totalPages <= 1;
        if (pagination.hidden) {
            pageList.innerHTML = "";
            return;
        }

        const numbers = pageWindow()
            .map((number) =>
                number === null
                    ? `<li><span class="pagination-ellipsis">&hellip;</span></li>`
                    : `<li>
                         <button class="pagination-link${number === page ? " is-current" : ""}"
                                 type="button" data-page="${number}"
                                 aria-label="Página ${number}"
                                 ${number === page ? 'aria-current="page"' : ""}>
                           ${number}
                         </button>
                       </li>`
            )
            .join("");

        pageList.innerHTML =
            arrow("fa-chevron-left", "Página anterior", page - 1, page <= 1) +
            numbers +
            arrow("fa-chevron-right", "Página seguinte", page + 1, page >= totalPages);
    }

    pageList.addEventListener("click", (event) => {
        const button = event.target.closest("[data-page]");
        if (!button || button.disabled) return;

        const wanted = Number(button.dataset.page);
        if (wanted === page || wanted < 1 || wanted > totalPages) return;

        page = wanted;
        loadProducts();
        // The grid starts above the fold on a filtered view; without this the
        // second page loads with its first row already scrolled past.
        document.getElementById("product-grid").scrollIntoView({ block: "start" });
    });

    // ----------------------------------------------------------------
    // Wiring
    // ----------------------------------------------------------------

    StoreFilters.onChange(() => {
        page = 1; // a changed filter invalidates the current page number
        syncSidebar();
        renderBadges();
        loadProducts();
    });

    (async function init() {
        searchInput.value = StoreFilters.get("q") || "";

        // Counts and colour sets first: the entries are rendered with them, not
        // patched afterwards.
        await Promise.all([loadFacets(), loadColorSets()]);
        await Promise.all(
            [...document.querySelectorAll("#filter-groups [data-filter-group]")].map(loadGroup)
        );

        syncSidebar();
        renderBadges();
        loadProducts();
    })();
})();
