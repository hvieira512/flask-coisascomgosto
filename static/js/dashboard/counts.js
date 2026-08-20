import { API, list } from "../core/api.js";

/**
 * How many pieces sit behind each id — the number every lookup table shows in
 * its last column, and the one a delete confirmation needs before it can say
 * what the deletion takes with it.
 *
 * `idsOf` returns the ids one product contributes to: its type is one, its
 * collection is one or none, its colour sets are as many as it has variants.
 * There were three of these, one per page, each fetching the whole catalogue and
 * reducing it its own way.
 *
 * Counted here rather than asked of the API because nothing exposes it, and a
 * page that already needs the products for its own table would otherwise pay for
 * a second answer to a question it can add up itself.
 */
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
