import { API } from "../../core/api.js";
import { removeLoading, renderLoading } from "../../core/utils.js";

const productList = document.getElementById("product-list");
const container = "#product-list";

const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

const renderEmptyMessage = () => {
    productList.innerHTML = `
        <div class="cell dash-empty">
            <span class="icon is-large has-text-grey-light"><i class="fa-solid fa-box-open fa-2x"></i></span>
            <p class="mt-3 has-text-grey">Ainda não há produtos.</p>
        </div>`;
};

const renderProduct = (product) => {
    const cell = document.createElement("div");
    cell.classList.add("cell");

    const image = product.primary_image
        ? `<img src="${escapeHtml(product.primary_image.url)}" alt="${escapeHtml(product.name)}">`
        : window.ProductPlaceholder.markup(product);

    const badges = product.variants
        .map((v) => window.ColorSet.badge(v.color_set))
        .join("");

    // Variant-pinned photographs live under each variant, not on the product.
    const photos = (product.images ?? []).length
        + product.variants.reduce((n, v) => n + (v.images ?? []).length, 0);

    cell.innerHTML = `
        <article class="card dash-product">
            <div class="card-image dash-product-media">${image}</div>
            <div class="card-content p-4">
                <p class="title is-6 mb-1">${escapeHtml(product.name)}</p>
                <p class="is-size-7 has-text-grey mb-3">
                    ${escapeHtml(product.type?.name ?? product.category.name)}
                    ${product.collection ? ` · ${escapeHtml(product.collection.name)}` : ""}
                </p>
                <div class="dash-product-badges">${badges}</div>
                <p class="is-size-7 has-text-grey mt-3">
                    <span class="icon is-small"><i class="fa-solid fa-image"></i></span>
                    ${photos} ${photos === 1 ? "fotografia" : "fotografias"}
                </p>
            </div>
            <footer class="card-footer">
                <a class="card-footer-item" data-product-action="view"
                   data-product-id="${product.id}" title="Ver">
                    <span class="icon"><i class="fa-solid fa-eye"></i></span>
                </a>
                <a class="card-footer-item" data-product-action="edit"
                   data-product-id="${product.id}" title="Editar">
                    <span class="icon"><i class="fa-solid fa-pencil"></i></span>
                </a>
                <a class="card-footer-item has-text-danger" data-product-action="delete"
                   data-product-id="${product.id}" title="Apagar">
                    <span class="icon"><i class="fa-solid fa-trash"></i></span>
                </a>
            </footer>
        </article>`;

    return cell;
};

const renderProducts = (products) => {
    productList.innerHTML = "";

    if (!products || products.length === 0) return renderEmptyMessage();

    products.forEach((product) => productList.appendChild(renderProduct(product)));
    document.getElementById("product-count").textContent =
        `${products.length} ${products.length === 1 ? "produto" : "produtos"}`;
};

export const fetchProducts = async () => {
    renderLoading(container);
    try {
        // limit=100: the dashboard lists the whole catalog. The API defaults to
        // 10, which silently hid four of fourteen products.
        const res = await window.Auth.authFetch(`${API.products.list}?limit=100`);
        if (!res.ok) throw new Error("Failed to fetch products");

        const { products } = await res.json();
        renderProducts(products);
    } catch (error) {
        Notify.error("Erro ao buscar produtos");
        console.error("Error fetching products:", error);
    }
    removeLoading(container);
};
