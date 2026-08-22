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

export async function request(url, { method = "GET", body, params, fallback, partial = false } = {}) {
    // The header is what proves to api/security.py that a write came from our
    // own code and not from a cross-site form using the session cookie.
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
        error.status = response.status;
        throw error;
    }

    if (response.status === 204) return null;

    const payload = await response.json().catch(() => null);
    if (!partial) assertWholeList(url, payload);
    return payload;
}

function assertWholeList(url, payload) {
    const envelope = payload?.pagination;
    if (!envelope) return;

    const received = envelope.page * envelope.limit;
    if (envelope.total <= received) return;
    if (new URL(url, window.location.origin).searchParams.has("page")) return;

    const error = new Error(
        `${url} answered ${received} of ${envelope.total} records. This screen ` +
        `works out its counts and filters from the whole list, so it would be ` +
        `built on part of one. The API caps limit at 100: this now needs a ` +
        `server-side filter or real pagination.`
    );
    error.truncated = true;
    throw error;
}

export async function requestOr(url, fallbackValue, options = {}) {
    try {
        return await request(url, options);
    } catch (error) {
        if (error.truncated) throw error;
        return fallbackValue;
    }
}

export async function list(url, key, { fallback, orEmpty = false, limit = 100 } = {}) {
    const options = { params: { limit }, fallback };

    if (!orEmpty) return (await request(url, options))[key] ?? [];

    try {
        return (await request(url, options))[key] ?? [];
    } catch (error) {
        if (error.truncated) throw error;
        return [];
    }
}

// Collection paths keep their trailing slash: flask-restx registers them that
// way, so "/api/materials" answers 308 and every list paid for two round trips.
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
    analytics: {
        overview: "/api/analytics/overview",
    },
    contacts: {
        get: "/api/contacts/",
        update: "/api/contacts/",
    },
};
