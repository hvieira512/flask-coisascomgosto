import { API, request, requestOr } from "../../core/api.js";


export async function listTypes() {
    const { product_types: types } = await request(
        `${API.productTypes.list}?limit=100`, { fallback: "Erro ao carregar os tipos." }
    );
    return types;
}

/** Pieces per type, so a row can say what deleting it would block. */
export async function countByType() {
    const payload = await requestOr(`${API.products.list}?limit=100`, { products: [] });

    const counts = new Map();
    for (const product of payload.products) {
        const id = product.type.id;
        counts.set(id, (counts.get(id) ?? 0) + 1);
    }
    return counts;
}

const SAVE_FAILED = "Não foi possível guardar.";

export const createType = (body) =>
    request(API.productTypes.create, { method: "POST", body, fallback: SAVE_FAILED });
export const updateType = (id, body) =>
    request(API.productTypes.update(id), { method: "PUT", body, fallback: SAVE_FAILED });
export const deleteType = (id) =>
    request(API.productTypes.delete(id), { method: "DELETE", fallback: SAVE_FAILED });

export async function listMaterials() {
    const { materials } = await request(
        `${API.materials.list}?limit=100`,
        { fallback: "Erro ao carregar os materiais." }
    );
    return materials;
}

export const createMaterial = (name) =>
    request(API.materials.create, { method: "POST", body: { name }, fallback: SAVE_FAILED });
export const updateMaterial = (id, name) =>
    request(API.materials.update(id), { method: "PUT", body: { name }, fallback: SAVE_FAILED });
export const deleteMaterial = (id) =>
    request(API.materials.delete(id), { method: "DELETE", fallback: SAVE_FAILED });
