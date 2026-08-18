/**
 * Every endpoint the dashboard talks to, and the one function that talks to them.
 *
 * Collection paths keep their trailing slash: flask-restx registers them that
 * way, so "/api/materials" answers 308 and every list and create paid for two
 * round trips instead of one.
 */

/**
 * A request that either returns the parsed body or throws something a toast can
 * show. Twenty-two call sites used to repeat this by hand, each with its own idea
 * of the failure message — one of them in English on a Portuguese dashboard.
 *
 * `fallback` is what to say when the API sends no message of its own. The API's
 * own message wins when there is one: "3 products still use this type" is worth
 * more than "could not delete".
 */
export async function request(url, { method = "GET", body, fallback } = {}) {
    const options = { method };

    if (body instanceof FormData) {
        // No Content-Type: the browser has to set the multipart boundary itself.
        options.body = body;
    } else if (body !== undefined) {
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.message || fallback || "Não foi possível concluir.");
    }

    // 204 and an empty 200 have nothing to parse; a DELETE returning the row does.
    if (response.status === 204) return null;
    return response.json().catch(() => null);
}

/** The same, for reads where an empty result is a better answer than a toast. */
export async function requestOr(url, fallbackValue) {
    try {
        return await request(url);
    } catch (error) {
        return fallbackValue;
    }
}

export const API = {
    materials: {
        list: "/api/materials/",
        get: (id) => `/api/materials/${id}`,
        create: "/api/materials/",
        update: (id) => `/api/materials/${id}`,
        delete: (id) => `/api/materials/${id}`,
    },
    products: {
        list: "/api/products/",
        get: (id) => `/api/products/${id}`,
        create: "/api/products/",
        update: (id) => `/api/products/${id}`,
        delete: (id) => `/api/products/${id}`,
        sizes: (id) => `/api/products/${id}/sizes`,
        variants: (id) => `/api/products/${id}/variants`,
        variant: (id, variantId) => `/api/products/${id}/variants/${variantId}`,
        images: (id) => `/api/products/${id}/images`,
        uploadImage: (id) => `/api/products/${id}/images/upload`,
        image: (id, imageId) => `/api/products/${id}/images/${imageId}`,
    },
    productTypes: {
        list: "/api/product-types/",
        get: (id) => `/api/product-types/${id}`,
        create: "/api/product-types/",
        update: (id) => `/api/product-types/${id}`,
        delete: (id) => `/api/product-types/${id}`,
    },
    collections: {
        list: "/api/collections/",
    },
    colorSets: {
        list: "/api/color-sets/",
    },
    sizes: {
        list: "/api/sizes/",
    },
    events: {
        list: "/api/events/",
        get: (id) => `/api/events/${id}`,
        create: "/api/events/",
        update: (id) => `/api/events/${id}`,
        delete: (id) => `/api/events/${id}`,
    },
    // core/auth.js is a classic script, so it cannot import from here and
    // hardcodes /api/auth/refresh itself.
    auth: {
        login: "/api/auth/login",
        register: "/api/auth/register",
    },
    contacts: {
        get: "/api/contacts/",
        update: "/api/contacts/",
    },
};
