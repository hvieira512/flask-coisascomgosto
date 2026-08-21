import { API, request } from "../../core/api.js";

/** Every photograph of a product, which means every colour's. */
export function allImages(product) {
    return product.variants.flatMap((variant) =>
        (variant.images ?? []).map((image) => ({ ...image, variant_id: variant.id }))
    );
}

/**
 * Uploads the chosen file and attaches it in one request.
 *
 * A colour is required, here and at the endpoint: a piece looks different in each
 * one, so a photograph of no particular colour is a photograph of the wrong one.
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
