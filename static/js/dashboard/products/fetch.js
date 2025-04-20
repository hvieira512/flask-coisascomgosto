import { API } from "../../core/api.js";
import { removeLoading, renderLoading } from "../../core/utils.js";

const productList = document.getElementById("product-list");
const container = "#product-list";

const renderEmptyMessage = () => {
    productList.innerHTML = `
        <div class="text-center text-muted mt-4 w-100">
            <p class="fs-5">Não há produtos inseridos.</p>
        </div>
    `;
};

const renderProduct = (product) => {
    console.log(product);
    const card = document.createElement('div');
    card.classList.add('product-card');

    card.innerHTML = `
        <div class="card shadow-sm h-100" data-bs-toggle="modal" data-bs-target="#checklistNOKsModal">
            <img src="https://placehold.co/260x160" class="card-img-top" alt="${product.name}">
            <div class="card-body d-flex flex-column">
                <h5 class="card-title">${product.name}</h5>
                <p class="card-text small">${product.description}</p>
                <p class="text-muted fw-bold small">Categoria: ${product.category_name}</p>
                <div class="mt-auto d-flex justify-content-evenly">
                    <button class="btn btn-outline-primary btn-sm" data-bs-toggle="modal" data-bs-target="#viewProductModal">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                    <button class="btn btn-outline-warning btn-sm" data-bs-toggle="modal" data-bs-target="#editProductModal">
                        <i class="fa-solid fa-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" data-bs-toggle="modal" data-bs-target="#deleteProductModal">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

    return card;
};

const renderProducts = (products) => {
    productList.innerHTML = '';

    if (!products || products.length === 0) {
        return renderEmptyMessage();
    }

    products.forEach(product => productList.appendChild(renderProduct(product)));
};

export const fetchProducts = async () => {
    renderLoading(container);
    try {
        const res = await fetch(API.products.list);
        if (!res.ok) throw new Error('Failed to fetch products');

        const products = await res.json();
        renderProducts(products);
    } catch (error) {
        toastr.error("Erro ao buscar produtos");
        console.error("Error fetching products:", error);
    }
    removeLoading(container);
};

