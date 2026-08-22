import { API, list } from "../core/api.js";

export async function pieceCounts(idsOf) {
    const products = await list(API.products.list, "products", { orEmpty: true });

    const counts = new Map();
    for (const product of products) {
        for (const id of idsOf(product)) {
            counts.set(id, (counts.get(id) ?? 0) + 1);
        }
    }
    return counts;
}

export const byType = () => pieceCounts((product) => [product.type.id]);
export const byCollection = () =>
    pieceCounts((product) => (product.collection ? [product.collection.id] : []));
export const byColorSet = () =>
    pieceCounts((product) => (product.variants ?? []).map((v) => v.color_set.id));
