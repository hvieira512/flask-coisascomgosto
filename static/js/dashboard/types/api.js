import { API } from "../../core/api.js";

/** Every write goes through here so one place turns a failure into a message. */
async function send(url, method, body) {
    const res = await fetch(url, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.message || "Não foi possível guardar.");
    }
    return res.status === 200 || res.status === 201 ? res.json() : null;
}

/** Top-level types, each with its sub-types resolved by the API. */
export async function listTypes() {
    const res = await fetch(`${API.productTypes.list}?roots_only=1&limit=100`);
    if (!res.ok) throw new Error("Erro ao carregar os tipos.");
    return (await res.json()).product_types;
}

/** Pieces per type, so a row can say what deleting it would block. */
export async function countByType() {
    const res = await fetch(`${API.products.list}?limit=100`);
    if (!res.ok) return new Map();

    const counts = new Map();
    for (const product of (await res.json()).products) {
        const id = product.type.id;
        counts.set(id, (counts.get(id) ?? 0) + 1);
    }
    return counts;
}

export const createType = (body) => send(API.productTypes.create, "POST", body);
export const updateType = (id, body) => send(API.productTypes.update(id), "PUT", body);
export const deleteType = (id) => send(API.productTypes.delete(id), "DELETE");

export async function listMaterials() {
    const res = await fetch(`${API.materials.list}?limit=100`);
    if (!res.ok) throw new Error("Erro ao carregar os materiais.");
    return (await res.json()).materials;
}

export const createMaterial = (name) => send(API.materials.create, "POST", { name });
export const updateMaterial = (id, name) => send(API.materials.update(id), "PUT", { name });
export const deleteMaterial = (id) => send(API.materials.delete(id), "DELETE");
