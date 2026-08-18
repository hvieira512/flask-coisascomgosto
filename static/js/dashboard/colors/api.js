import { API, request, requestOr } from "../../core/api.js";


const SAVE_FAILED = "Não foi possível guardar.";

export async function listColorSets() {
    const { color_sets: sets } = await request(
        `${API.colorSets.list}?limit=100`,
        { fallback: "Erro ao carregar os conjuntos." }
    );
    return sets;
}

export async function listColors() {
    const { colors } = await request(
        `${API.colors.list}?limit=100`, { fallback: "Erro ao carregar as cores." }
    );
    return colors;
}

export async function listCollections() {
    const { collections } = await requestOr(
        `${API.collections.list}?limit=100`, { collections: [] }
    );
    return collections;
}

/**
 * Pieces per colour set, so a row can say what deleting it would take with it.
 *
 * Deleting a set deletes every variant using it — and a variant's photos. The
 * owners get to see that number before they confirm.
 */
export async function countByColorSet() {
    const { products } = await requestOr(`${API.products.list}?limit=100`, { products: [] });

    const counts = new Map();
    for (const product of products) {
        for (const variant of product.variants ?? []) {
            const id = variant.color_set.id;
            counts.set(id, (counts.get(id) ?? 0) + 1);
        }
    }
    return counts;
}

export const createColorSet = (body) =>
    request(API.colorSets.create, { method: "POST", body, fallback: SAVE_FAILED });
export const updateColorSet = (id, body) =>
    request(API.colorSets.update(id), { method: "PUT", body, fallback: SAVE_FAILED });
export const deleteColorSet = (id) =>
    request(API.colorSets.delete(id), { method: "DELETE", fallback: SAVE_FAILED });

export const createColor = (body) =>
    request(API.colors.create, { method: "POST", body, fallback: SAVE_FAILED });
export const updateColor = (id, body) =>
    request(API.colors.update(id), { method: "PUT", body, fallback: SAVE_FAILED });
export const deleteColor = (id) =>
    request(API.colors.delete(id), { method: "DELETE", fallback: SAVE_FAILED });
