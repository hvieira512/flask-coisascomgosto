import { API, request, requestOr } from "../../core/api.js";


const SAVE_FAILED = "Não foi possível guardar.";

export async function listCollections() {
    const { collections } = await request(
        `${API.collections.list}?limit=100`,
        { fallback: "Erro ao carregar as colecções." }
    );
    return collections;
}

/** Pieces per collection, so a row can say what deleting it would detach. */
export async function countByCollection() {
    const { products } = await requestOr(`${API.products.list}?limit=100`, { products: [] });

    const counts = new Map();
    for (const product of products) {
        if (!product.collection) continue;
        const id = product.collection.id;
        counts.set(id, (counts.get(id) ?? 0) + 1);
    }
    return counts;
}

export const createCollection = (body) =>
    request(API.collections.create, { method: "POST", body, fallback: SAVE_FAILED });
export const updateCollection = (id, body) =>
    request(API.collections.update(id), { method: "PUT", body, fallback: SAVE_FAILED });
export const deleteCollection = (id) =>
    request(API.collections.delete(id), { method: "DELETE", fallback: SAVE_FAILED });

export function uploadCover(id, file) {
    const form = new FormData();
    form.append("file", file);
    return request(API.collections.cover(id), {
        method: "POST",
        body: form,
        fallback: "Não foi possível guardar a capa.",
    });
}

export const removeCover = (id) =>
    request(API.collections.cover(id), {
        method: "DELETE",
        fallback: "Não foi possível remover a capa.",
    });

export async function listColorSets() {
    const { color_sets: sets } = await request(
        `${API.colorSets.list}?limit=100`,
        { fallback: "Erro ao carregar os conjuntos de cores." }
    );
    return sets;
}

/** A colour set belongs to one collection, so this moves them, not links them. */
export const setColorSets = (id, colorSetIds) =>
    request(API.collections.colorSets(id), {
        method: "PUT",
        body: { color_set_ids: colorSetIds },
        fallback: "Não foi possível guardar os conjuntos de cores.",
    });
