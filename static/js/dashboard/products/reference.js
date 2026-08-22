import { API, list } from "../../core/api.js";

let cache = null;

const listOf = (url, key) => list(url, key, { orEmpty: true });

export async function reference({ refresh = false } = {}) {
    if (cache && !refresh) return cache;

    const [materials, types, collections, colorSets, sizes] = await Promise.all([
        listOf(API.materials.list, "materials"),
        listOf(API.productTypes.list, "product_types"),
        listOf(API.collections.list, "collections"),
        listOf(API.colorSets.list, "color_sets"),
        listOf(API.sizes.list, "sizes"),
    ]);

    cache = { materials, types, collections, colorSets, sizes };
    return cache;
}

export function typeOptions(types) {
    return types.map((type) => ({ id: type.id, label: type.name }));
}
