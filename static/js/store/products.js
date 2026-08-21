/**
 * Catalog page.
 *
 * Four pieces render the same StoreFilters state — the sidebar, the collection
 * rail, the applied-filter badges and the grid — so choosing a filter anywhere
 * updates all of them from one place: the onChange at the foot of this file.
 *
 * This file holds only what is shared: the page number, the per-option counts
 * both the sidebar and the rail read, and the request for the products
 * themselves. Each piece lives in catalogue/.
 */

import { API, request } from "../core/api.js";
import { StoreFilters } from "./filters.js";
import { mountBadges } from "./catalogue/badges.js";
import { mountPagination } from "./catalogue/pagination.js";
import { mountRail } from "./catalogue/rail.js";
import { mountSidebar } from "./catalogue/sidebar.js";
import { productCard } from "./catalogue/cards.js";

(function () {
    const grid = document.getElementById("product-grid");
    const emptyNotice = document.getElementById("grid-empty");
    const resultCount = document.getElementById("result-count");
    const searchInput = document.getElementById("filter-search");

    let page = 1;

    /** Per-option product counts, so a sidebar entry and a rail card can each say
     *  what they hold. One request, read by both. */
    async function loadFacets() {
        try {
            const payload = await request("/api/products/facets");
            return Object.fromEntries(
                Object.entries(payload).map(([key, rows]) => [
                    key,
                    new Map(rows.map((row) => [row.id, row.count])),
                ])
            );
        } catch (error) {
            return {};
        }
    }

    const badges = mountBadges(searchInput);
    const pagination = mountPagination((wanted) => {
        page = wanted;
        loadProducts();
        // The grid starts above the fold on a filtered view; without this the
        // second page loads with its first row already scrolled past.
        grid.scrollIntoView({ block: "start" });
    });

    let searchTimer;
    searchInput.addEventListener("input", (event) => {
        clearTimeout(searchTimer);
        const value = event.target.value.trim();
        searchTimer = setTimeout(() => StoreFilters.set("q", value || null), 250);
    });

    async function loadProducts() {
        const params = {
            ...StoreFilters.active(),
            page,
            limit: 9,
            photographed_first: 1,
        };

        let payload;
        try {
            payload = await request(API.products.list, { params });
        } catch (error) {
            grid.innerHTML = "";
            emptyNotice.hidden = false;
            emptyNotice.textContent = "Não foi possível carregar os produtos.";
            return;
        }

        const products = payload.products || [];
        grid.innerHTML = products.map(productCard).join("");

        emptyNotice.hidden = products.length > 0;
        emptyNotice.textContent = "Nenhum produto corresponde aos filtros escolhidos.";

        const { total, pages } = payload.pagination;
        resultCount.textContent = total === 1 ? "1 produto" : `${total} produtos`;
        pagination.render(page, pages || 1);
    }

    (async function init() {
        searchInput.value = StoreFilters.get("q") || "";

        // Counts first: the entries and the cards are rendered with their numbers
        // rather than patched afterwards.
        const facets = await loadFacets();
        const [sidebar, rail] = await Promise.all([
            mountSidebar(facets),
            mountRail(facets),
        ]);

        const draw = () => {
            sidebar.sync();
            rail.render();
            badges.render();
            loadProducts();
        };

        StoreFilters.onChange(() => {
            page = 1; // a changed filter invalidates the current page number
            draw();
        });

        draw();
    })();
})();
