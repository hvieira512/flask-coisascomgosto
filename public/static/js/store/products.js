import { API, list, request } from "../core/api.js";
import { StoreFilters } from "./filters.js";
import { mountBadges } from "./catalogue/badges.js";
import { mountCollections } from "./catalogue/collections.js";
import { mountPagination } from "./catalogue/pagination.js";
import { mountSidebar } from "./catalogue/sidebar.js";
import { productCard } from "./catalogue/cards.js";
import { Track } from "./track.js";

(function () {
    const main = document.querySelector(".catalogue-main");
    const grid = document.getElementById("product-grid");
    const collectionGrid = document.getElementById("collection-grid");
    const crumbs = document.getElementById("grid-crumbs");
    const crumbHere = crumbs.querySelector("[data-crumb-here]");
    const emptyNotice = document.getElementById("grid-empty");
    const resultCount = document.getElementById("result-count");
    const searchInput = document.getElementById("filter-search");

    const pieces = (n) => (n === 1 ? "1 peça" : `${n} peças`);

    let page = 1;
    let reported = null;
    let sidebar;
    // The collections with pieces at all. With none, the page is the pieces alone.
    let collections = [];
    // Filters change faster than the API answers; only the latest draw may paint.
    let drawing = 0;

    const facetCache = new Map();

    function facets(params = {}) {
        const key = JSON.stringify(params);
        if (!facetCache.has(key)) {
            const loading = request(API.products.facets, { params }).then((payload) => ({
                total: payload.total ?? 0,
                ...Object.fromEntries(
                    Object.entries(payload)
                        .filter(([, rows]) => Array.isArray(rows))
                        .map(([facet, rows]) => [facet, new Map(rows.map((row) => [row.id, row.count]))])
                ),
            }));
            loading.catch(() => facetCache.delete(key));
            facetCache.set(key, loading);
        }
        return facetCache.get(key).catch(() => ({ total: 0 }));
    }

    const badges = mountBadges(searchInput);
    const pagination = mountPagination((wanted) => {
        page = wanted;
        loadProducts();
        grid.scrollIntoView({ block: "start" });
    });

    const tiles = mountCollections((id, name) => {
        if (id) {
            StoreFilters.set("collection_id", id, name, { push: true });
            Track.filter("Colecção", name);
        } else {
            StoreFilters.set("all", "1", null, { push: true });
        }
        if (main.getBoundingClientRect().top < 0) main.scrollIntoView({ block: "start" });
    });

    crumbs.addEventListener("click", (event) => {
        const back = event.target.closest("a[data-crumb-collections]");
        if (!back) return;

        event.preventDefault();
        searchInput.value = "";
        StoreFilters.leave();
    });

    window.addEventListener("popstate", () => {
        StoreFilters.reload();
        searchInput.value = StoreFilters.get("q") || "";
    });

    let searchTimer;
    searchInput.addEventListener("input", (event) => {
        clearTimeout(searchTimer);
        const value = event.target.value.trim();
        searchTimer = setTimeout(() => StoreFilters.set("q", value || null), 250);
    });

    // Collections first, unless one is open, everything was asked for, or
    // something was searched.
    const showingCollections = () =>
        collections.length > 0
        && !StoreFilters.get("collection_id") && !StoreFilters.get("all") && !StoreFilters.get("q");

    async function loadCollections(token) {
        grid.hidden = true;
        crumbs.hidden = true;
        pagination.render(1, 1);
        collectionGrid.hidden = false;
        collectionGrid.classList.toggle("is-loading", collectionGrid.children.length > 0);

        const { type_id, material_id } = StoreFilters.active();
        const counts = await facets({ type_id, material_id });
        if (token !== drawing) return;

        collectionGrid.classList.remove("is-loading");
        tiles.render(collections, counts.collections ?? new Map(), counts.total);

        emptyNotice.hidden = counts.total > 0;
        emptyNotice.textContent = "Nenhuma peça corresponde aos filtros escolhidos.";
        resultCount.textContent = pieces(counts.total);
    }

    async function loadProducts(token = drawing) {
        collectionGrid.hidden = true;
        grid.hidden = false;

        const openId = StoreFilters.get("collection_id");
        crumbs.hidden = collections.length === 0;
        crumbHere.textContent = openId ? StoreFilters.labelFor("collection_id", openId) : "Todas as peças";

        // `all` only says which grid is on screen; the API would not know it.
        const { all, ...filters } = StoreFilters.active();
        const params = { ...filters, page, limit: 9, photographed_first: 1 };

        grid.classList.toggle("is-loading", grid.children.length > 0);

        let payload;
        try {
            payload = await request(API.products.list, { params });
        } catch (error) {
            if (token !== drawing) return;
            grid.classList.remove("is-loading");
            grid.innerHTML = "";
            emptyNotice.hidden = false;
            emptyNotice.textContent = "Não foi possível carregar as peças.";
            return;
        }
        if (token !== drawing) return;

        grid.classList.remove("is-loading");
        const products = payload.products || [];
        grid.innerHTML = products.map(productCard).join("");

        emptyNotice.hidden = products.length > 0;
        emptyNotice.textContent = "Nenhuma peça corresponde aos filtros escolhidos.";

        const { total, pages } = payload.pagination;
        resultCount.textContent = pieces(total);
        pagination.render(page, pages || 1);

        const term = StoreFilters.get("q");
        if (term && term !== reported) {
            reported = term;
            Track.search(term, total);
        }
    }

    function draw() {
        const token = ++drawing;
        sidebar.sync();
        badges.render();

        const openId = StoreFilters.get("collection_id");
        facets(openId ? { collection_id: openId } : {}).then((counts) => {
            if (token === drawing) sidebar.updateCounts(counts);
        });

        return showingCollections() ? loadCollections(token) : loadProducts(token);
    }

    (async function init() {
        searchInput.value = StoreFilters.get("q") || "";
        // Not known yet whether there are collections; the skeleton is the likelier guess.
        if (!StoreFilters.get("collection_id") && !StoreFilters.get("all") && !StoreFilters.get("q")) {
            collectionGrid.hidden = false;
            tiles.skeleton();
        }

        const [counts, every] = await Promise.all([
            facets(),
            list(API.collections.list, "collections", { orEmpty: true }),
        ]);
        every.forEach((collection) => StoreFilters.registerLabel("collection_id", collection.id, collection.name));
        collections = every.filter((collection) => (counts.collections?.get(collection.id) ?? 0) > 0);

        sidebar = await mountSidebar(counts);

        StoreFilters.onChange(() => {
            page = 1;
            draw();
        });

        draw();
    })();
})();
