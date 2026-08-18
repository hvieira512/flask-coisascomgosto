import { API } from "../../core/api.js";

/**
 * The lookup lists every product form needs: types, materials, collections,
 * colour sets and sizes. Fetched once and reused, since they change rarely and
 * every modal would otherwise refetch them.
 */
let cache = null;

const listOf = async (url, key) => {
    const res = await fetch(`${url}?limit=100`);
    if (!res.ok) return [];
    return (await res.json())[key] ?? [];
};

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

/** Flattens the type tree into "Caixa · Caixa redonda" options. */
export function typeOptions(types) {
    const options = [];
    types.forEach((type) => {
        options.push({ id: type.id, label: type.name });
        (type.sub_types ?? []).forEach((sub) =>
            options.push({ id: sub.id, label: `${type.name} · ${sub.name}` })
        );
    });
    return options;
}
