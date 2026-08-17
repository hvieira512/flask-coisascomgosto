/**
 * Thin fetch wrapper for the storefront.
 *
 * Every page talks to the same JSON API the dashboard uses, so the catalog has
 * one source of truth.
 */
window.StoreApi = (function () {
    async function get(path, params) {
        const url = new URL(path, window.location.origin);

        Object.entries(params || {}).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== "") {
                url.searchParams.set(key, value);
            }
        });

        const response = await fetch(url, {
            headers: { Accept: "application/json" },
        });

        if (!response.ok) {
            const error = new Error(`Request failed: ${response.status}`);
            error.status = response.status;
            throw error;
        }

        return response.json();
    }

    return {
        get,
        products: (params) => get("/api/products/", params),
        product: (id) => get(`/api/products/${id}`),
    };
})();
