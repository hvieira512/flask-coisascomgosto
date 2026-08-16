// -------------------
// Generic Fetch Wrappers
// -------------------

export async function fetchData(url, headers = {}) {
    try {
        const response = await fetch(url, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                ...headers,
            },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || `Failed to fetch: ${url}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`fetchData error for ${url}:`, error);
        throw error;
    }
}

export async function postData(url, data = {}, headers = {}) {
    const res = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...headers,
        },
        body: JSON.stringify(data),
    });

    const contentType = res.headers.get("content-type");
    if (!res.ok) {
        const err = contentType?.includes("application/json")
            ? await res.json()
            : await res.text();
        throw new Error(err.error || err || "Unknown error");
    }

    return await res.json();
}

export async function putData(url, data = {}, headers = {}) {
    const res = await fetch(url, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            ...headers,
        },
        body: JSON.stringify(data),
    });
    return await res.json();
}

export async function deleteData(url, headers = {}) {
    const res = await fetch(url, {
        method: "DELETE",
        headers: {
            "Content-Type": "application/json",
            ...headers,
        },
    });
    return await res.json();
}

// -------------------
// Registered Endpoints
// -------------------

export const API = {
    categories: {
        list: "/api/categories",
        get: (id) => `/api/categories/${id}`,
        create: "/api/categories",
        update: (id) => `/api/categories/${id}`,
        delete: (id) => `/api/categories/${id}`,
    },
    products: {
        list: "/api/products",
        get: (id) => `/api/products/${id}`,
        create: "/api/products",
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
        list: "/api/product-types",
        get: (id) => `/api/product-types/${id}`,
    },
    collections: {
        list: "/api/collections",
    },
    colorSets: {
        list: "/api/color-sets",
    },
    colors: {
        list: "/api/colors",
    },
    sizes: {
        list: "/api/sizes",
    },
    events: {
        list: "/api/events",
    },
    users: {
        list: "/api/users",
        get: (id) => `/api/users/${id}`,
        update: (id) => `/api/users/${id}`,
        delete: (id) => `/api/users/${id}`,
    },
    auth: {
        login: "/api/auth/login",
        register: "/api/auth/register",
        refresh: "/api/auth/refresh",
        me: "/api/auth/me",
        logout: "/api/auth/logout",
    },
    contacts: {
        get: "/api/contacts/",
        update: "/api/contacts/",
    },
};
