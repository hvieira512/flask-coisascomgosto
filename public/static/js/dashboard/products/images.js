import { API, request } from "../../core/api.js";

export function allImages(product) {
    return product.variants.flatMap((variant) =>
        (variant.images ?? []).map((image) => ({ ...image, variant_id: variant.id }))
    );
}

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
