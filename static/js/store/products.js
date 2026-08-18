/**
 * Catalog page: filter sidebar, applied-filter badges and the product grid.
 *
 * The sidebar and the badge row are two renderings of the same StoreFilters
 * state, so selecting an entry in the sidebar and removing its badge are the
 * same operation.
 */
(function () {
    const grid = document.getElementById("product-grid");
    const emptyNotice = document.getElementById("grid-empty");
    const badgeRow = document.getElementById("active-filters");
    const resultCount = document.getElementById("result-count");
    const clearButton = document.getElementById("clear-filters");
    const searchInput = document.getElementById("filter-search");
    const pagination = document.getElementById("pagination");
    const pageIndicator = document.getElementById("page-indicator");

    let page = 1;
    let totalPages = 1;

    // ----------------------------------------------------------------
    // Sidebar
    // ----------------------------------------------------------------

    /** Fill one sidebar group from its API endpoint. */
    async function loadGroup(list) {
        const { filterGroup, endpoint, collectionKey } = list.dataset;

        let payload;
        try {
            payload = await StoreApi.get(endpoint, { limit: 100 });
        } catch (error) {
            list.innerHTML = '<li><span class="has-text-grey is-size-7">Indisponível</span></li>';
            return;
        }

        const items = payload[collectionKey] || [];
        list.innerHTML = items.map((item) => renderEntry(filterGroup, item)).join("");

        // Cache names so badges can render before the sidebar is consulted.
        items.forEach((item) =>
            StoreFilters.registerLabel(filterGroup, item.id, item.name)
        );
    }

    function renderEntry(group, item) {
        return `
          <li>
            <a data-filter-group="${group}" data-filter-value="${item.id}"
               data-filter-label="${escapeHtml(item.name)}">
              <span>${escapeHtml(item.name)}</span>
            </a>
          </li>`;
    }

    /** Highlight whichever sidebar entries match the current state. */
    function syncSidebar() {
        document.querySelectorAll("#filter-groups a[data-filter-group]").forEach((link) => {
            const { filterGroup, filterValue } = link.dataset;
            link.classList.toggle("is-active", StoreFilters.get(filterGroup) === filterValue);
        });
    }

    document.getElementById("filter-groups").addEventListener("click", (event) => {
        const link = event.target.closest("a[data-filter-group]");
        if (!link) return;

        event.preventDefault();
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
     * One Bulma tag per active filter, shaped "Group: Value ×".
     * Clicking anywhere on the tag removes that filter.
     */
    function renderBadges(activeFilters) {
        const entries = Object.entries(activeFilters);
        badgeRow.hidden = entries.length === 0;
        clearButton.hidden = entries.length === 0;

        badgeRow.innerHTML = entries
            .map(([group, value]) => {
                const groupLabel = StoreFilters.GROUPS[group].label;
                const valueLabel = StoreFilters.labelFor(group, value);
                return `
                  <span class="tag is-dark is-medium filter-badge" data-remove-filter="${group}"
                        role="button" tabindex="0"
                        title="Remover filtro ${escapeHtml(groupLabel)}">
                    ${escapeHtml(groupLabel)}: ${escapeHtml(valueLabel)}
                    <button class="delete is-small" aria-label="Remover ${escapeHtml(groupLabel)}"></button>
                  </span>`;
            })
            .join("");
    }

    badgeRow.addEventListener("click", (event) => {
        const badge = event.target.closest("[data-remove-filter]");
        if (!badge) return;

        const group = badge.dataset.removeFilter;
        StoreFilters.clear(group);
        if (group === "q") searchInput.value = "";
    });

    // Keyboard parity: the badge is focusable, so Enter/Space must remove it too.
    badgeRow.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;

        const badge = event.target.closest("[data-remove-filter]");
        if (!badge) return;

        event.preventDefault();
        const group = badge.dataset.removeFilter;
        StoreFilters.clear(group);
        if (group === "q") searchInput.value = "";
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
        const cells = sets.slice(0, visible).map(window.ColorSet.badge);

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

        pagination.hidden = totalPages <= 1;
        pageIndicator.textContent = `${page} / ${totalPages}`;
        pagination.querySelector("[data-page-prev]").disabled = page <= 1;
        pagination.querySelector("[data-page-next]").disabled = page >= totalPages;
    }

    pagination.querySelector("[data-page-prev]").addEventListener("click", () => {
        if (page > 1) {
            page -= 1;
            loadProducts();
        }
    });

    pagination.querySelector("[data-page-next]").addEventListener("click", () => {
        if (page < totalPages) {
            page += 1;
            loadProducts();
        }
    });

    // ----------------------------------------------------------------
    // Wiring
    // ----------------------------------------------------------------

    StoreFilters.onChange((activeFilters) => {
        page = 1; // a changed filter invalidates the current page number
        syncSidebar();
        renderBadges(activeFilters);
        loadProducts();
    });

    (async function init() {
        searchInput.value = StoreFilters.get("q") || "";

        await Promise.all(
            [...document.querySelectorAll("#filter-groups [data-filter-group]")].map(loadGroup)
        );

        syncSidebar();
        renderBadges(StoreFilters.active());
        loadProducts();
    })();
})();
