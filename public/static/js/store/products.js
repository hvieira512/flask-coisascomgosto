import { API, request } from "../core/api.js";
import { StoreFilters } from "./filters.js";
import { mountBadges } from "./catalogue/badges.js";
import { mountPagination } from "./catalogue/pagination.js";
import { mountRail } from "./catalogue/rail.js";
import { mountSidebar } from "./catalogue/sidebar.js";
import { productCard } from "./catalogue/cards.js";
import { Track } from "./track.js";

(function () {
    const grid = document.getElementById("product-grid");
    const emptyNotice = document.getElementById("grid-empty");
    const resultCount = document.getElementById("result-count");
    const searchInput = document.getElementById("filter-search");

    let page = 1;
    let reported = null;

    async function loadFacets() {
        try {
            const payload = await request(API.products.facets);
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

        const term = StoreFilters.get("q");
        if (term && term !== reported) {
            reported = term;
            Track.search(term, total);
        }
    }

    (async function init() {
        searchInput.value = StoreFilters.get("q") || "";

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
            page = 1;
            draw();
        });

        draw();
    })();
})();
