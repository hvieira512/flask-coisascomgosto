/**
 * Every endpoint the front end talks to, and the one function that talks to them.
 *
 * Collection paths keep their trailing slash: flask-restx registers them that
 * way, so "/api/materials" answers 308 and every list and create paid for two
 * round trips instead of one.
 */

/**
 * A query string from a plain object.
 *
 * An array becomes repeated keys — ?type_id=1&type_id=5 — which is how the API
 * takes several values for one filter. Empty and absent values are dropped, so a
 * caller can pass its whole filter state without sifting it first.
 */
function query(path, params) {
    const url = new URL(path, window.location.origin);

    for (const [key, value] of Object.entries(params)) {
        if (Array.isArray(value)) value.forEach((one) => url.searchParams.append(key, one));
        else if (value !== null && value !== undefined && value !== "") {
            url.searchParams.set(key, value);
        }
    }
    return url;
}

/**
 * A request that either returns the parsed body or throws something a toast can
 * show. Twenty-two call sites used to repeat this by hand, each with its own idea
 * of the failure message — one of them in English on a Portuguese dashboard.
 *
 * `fallback` is what to say when the API sends no message of its own. The API's
 * own message wins when there is one: "3 products still use this type" is worth
 * more than "could not delete".
 *
 * The storefront had a second wrapper of its own for a while. It knew how to
 * build a query string and this one did not, so the dashboard concatenated
 * "?limit=100" by hand at fifteen call sites; this one knew how to report a
 * failure in Portuguese and that one did not, so a shopper got
 * "Request failed: 500". Neither gap was worth two implementations.
 */
export async function request(url, { method = "GET", body, params, fallback } = {}) {
    // Proves to api/security.py that a write came from our own code and not from
    // a cross-site form using the session cookie. Sent on reads too, since the
    // header is what identifies the caller, not a per-request decision.
    const options = { method, headers: { "X-Requested-With": "fetch" } };
    if (params) url = query(url, params);

    if (body instanceof FormData) {
        // No Content-Type: the browser has to set the multipart boundary itself.
        options.body = body;
    } else if (body !== undefined) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        const error = new Error(payload.message || fallback || "Não foi possível concluir.");
        // The API answers in English, by design — it is a documented REST API. A
        // caller that would rather say it in Portuguese needs to know which
        // failure this was.
        error.status = response.status;
        throw error;
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

/**
 * One list endpoint's own array, unwrapped from its pagination envelope.
 *
 * `key` is what the envelope calls it: /api/color-sets/ answers
 * `{ color_sets: [...], pagination: {...} }`. limit=100 because every list on
 * these screens is a lookup the owners scroll, not a page they leaf through —
 * it used to be spelled out at fifteen call sites.
 *
 * `orEmpty` is for a list that is context rather than content: a filter bar with
 * no options is worth more than a page that refused to load.
 */
export async function list(url, key, { fallback, orEmpty = false, limit = 100 } = {}) {
    const options = { params: { limit }, fallback };

    if (!orEmpty) return (await request(url, options))[key] ?? [];

    try {
        return (await request(url, options))[key] ?? [];
    } catch (error) {
        return [];
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
        create: "/api/collections/",
        update: (id) => `/api/collections/${id}`,
        delete: (id) => `/api/collections/${id}`,
        cover: (id) => `/api/collections/${id}/cover`,
        colorSets: (id) => `/api/collections/${id}/color-sets`,
    },
    colorSets: {
        list: "/api/color-sets/",
        create: "/api/color-sets/",
        update: (id) => `/api/color-sets/${id}`,
        delete: (id) => `/api/color-sets/${id}`,
    },
    colors: {
        list: "/api/colors/",
        create: "/api/colors/",
        update: (id) => `/api/colors/${id}`,
        delete: (id) => `/api/colors/${id}`,
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
    auth: {
        login: "/api/auth/login",
        register: "/api/auth/register",
    },
    contacts: {
        get: "/api/contacts/",
        update: "/api/contacts/",
    },
};
