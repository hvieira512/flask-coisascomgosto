import { API } from "../../core/api.js";
import { removeLoading, renderLoading } from "../../core/utils.js";

const productList = document.getElementById("product-list");
const container = "#product-list";

const renderEmptyMessage = () => {
    productList.innerHTML = `
        <div class="column is-full">
            <div class="notification is-light has-text-centered">
                Não há produtos inseridos.
            </div>
        </div>
    `;
};

const renderProduct = (product) => {
    const column = document.createElement("div");
    column.classList.add("cell");

    // Modals are opened via data-modal-target, handled by dashboard/menus.js.
    const image = product.primary_image
        ? `<img src="${product.primary_image.url}" alt="${product.name}">`
        : window.ProductPlaceholder.markup(product);

    column.innerHTML = `
        <div class="card product-card">
            <div class="card-image">${image}</div>
            <div class="card-content">
                <p class="title is-6 mb-1">${product.name}</p>
                <p class="is-size-7 has-text-grey">${product.description ?? ""}</p>
                <p class="is-size-7 has-text-weight-semibold mt-2">${product.category.name}</p>
            </div>
            <footer class="card-footer">
                <a class="card-footer-item" data-modal-target="viewProductModal" title="Ver">
                    <span class="icon"><i class="fa-solid fa-eye"></i></span>
                </a>
                <a class="card-footer-item" data-modal-target="editProductModal" title="Editar">
                    <span class="icon"><i class="fa-solid fa-pencil"></i></span>
                </a>
                <a class="card-footer-item has-text-danger" data-modal-target="deleteProductModal" title="Apagar">
                    <span class="icon"><i class="fa-solid fa-trash"></i></span>
                </a>
            </footer>
        </div>
    `;

    return column;
};

const renderProducts = (products) => {
    productList.innerHTML = "";

    if (!products || products.length === 0) {
        return renderEmptyMessage();
    }

    products.forEach((product) =>
        productList.appendChild(renderProduct(product))
    );
};

export const fetchProducts = async () => {
    renderLoading(container);
    try {
        // authFetch refreshes the access token and retries on a 401.
        const res = await window.Auth.authFetch(API.products.list);
        if (!res.ok) throw new Error("Failed to fetch products");

        const { products } = await res.json();
        renderProducts(products);
    } catch (error) {
        Notify.error("Erro ao buscar produtos");
        console.error("Error fetching products:", error);
    }
    removeLoading(container);
};
