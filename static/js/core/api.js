export const API = {
    materials: {
        list: "/api/materials",
        get: (id) => `/api/materials/${id}`,
        create: "/api/materials",
        update: (id) => `/api/materials/${id}`,
        delete: (id) => `/api/materials/${id}`,
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
        create: "/api/product-types",
        update: (id) => `/api/product-types/${id}`,
        delete: (id) => `/api/product-types/${id}`,
    },
    collections: {
        list: "/api/collections",
    },
    colorSets: {
        list: "/api/color-sets",
    },
    sizes: {
        list: "/api/sizes",
    },
    events: {
        list: "/api/events",
        get: (id) => `/api/events/${id}`,
        create: "/api/events",
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
