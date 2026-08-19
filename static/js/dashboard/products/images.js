import { API, request } from "../../core/api.js";

/**
 * Every photograph of a product, from both places the API keeps them:
 * `product.images` holds only the product-wide ones, and each variant carries
 * its own. Reading just the first showed nothing for a pinned photograph.
 */
export function allImages(product) {
    const pinned = product.variants.flatMap((variant) =>
        (variant.images ?? []).map((image) => ({ ...image, variant_id: variant.id }))
    );
    return [...(product.images ?? []), ...pinned];
}

/**
 * Uploads the chosen file and attaches it in one request.
 *
 * A colour is required. The API still accepts a photograph without one — which is how
 * the seeded photographs came to have none — but nothing here creates another.
 */
export async function uploadImage(productId, { file, variantId, alt }) {
    if (!file) throw new Error("Escolha uma fotografia.");
    if (!variantId) throw new Error("Escolha a cor a que a fotografia pertence.");

    const body = new FormData();
    body.append("file", file);
    body.append("variant_id", variantId);
    if (alt) body.append("alt", alt);

    await request(API.products.uploadImage(productId), {
        method: "POST",
        body,
        fallback: "Não foi possível carregar a fotografia.",
    });
}

export async function removeImage(productId, imageId) {
    await request(API.products.image(productId, imageId), {
        method: "DELETE",
        fallback: "Não foi possível remover a fotografia.",
    });
}
