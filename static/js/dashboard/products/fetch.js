import { API, request } from "../../core/api.js";
import { isFiltered, photoFilter, query } from "./filters.js";

const productList = document.getElementById("product-list");
const COLUMNS = 5;

const renderEmptyMessage = () => {
    const filtered = isFiltered();
    productList.innerHTML = `
        <tr>
          <td colspan="${COLUMNS}" class="has-text-centered py-6">
            <span class="icon is-large has-text-grey-light">
              <i class="fa-solid ${filtered ? "fa-filter-circle-xmark" : "fa-box-open"} fa-2x"></i>
            </span>
            <p class="mt-3 has-text-grey">
              ${filtered
                  ? "Nenhuma peça corresponde aos filtros."
                  : "Ainda não há peças no catálogo."}
            </p>
          </td>
        </tr>`;
};

/** Photographs live on the product and on each variant. */
const photoCount = (product) =>
    (product.images ?? []).length
    + product.variants.reduce((n, v) => n + (v.images ?? []).length, 0);

/**
 * A photograph count is the one number on this page that needs acting on, so
 * zero is a state and not just a smaller number.
 */
const photoCell = (product) => {
    const photos = photoCount(product);
    if (photos === 0) {
        return `<span class="tag is-rounded chip is-attention">
                  <span class="icon is-small"><i class="fa-solid fa-triangle-exclamation"></i></span>
                  <span>Sem fotografia</span>
                </span>`;
    }
    return `<span class="data has-text-grey">${photos} ${photos === 1 ? "foto" : "fotos"}</span>`;
};

const row = (product) => {
    const tr = document.createElement("tr");
    tr.dataset.productId = product.id;

    const image = product.primary_image
        ? `<img class="dash-thumb" src="${escapeHtml(product.primary_image.url)}"
                alt="${escapeHtml(product.name)}">`
        : window.ProductPlaceholder.markup(product);

    // Capped at three so a piece offered in five colours does not make its row
    // twice the height of its neighbours and break the scan down the column.
    // The full list is one click away, in the row's own Cores tab.
    const SHOWN = 3;
    const shown = product.variants.slice(0, SHOWN);
    const rest = product.variants.length - shown.length;

    const colours = product.variants.length
        ? `<span class="is-flex is-align-items-center is-gap-1">
             ${shown.map((v) => window.ColorSet.badge(v.color_set)).join("")}
             ${rest ? `<span class="data has-text-grey">+${rest}</span>` : ""}
           </span>`
        : `<span class="tag is-rounded chip is-quiet">Sem cores</span>`;

    // The type is what the piece is; the collection is which family it belongs
    // to. Both under the name, because the name alone rarely distinguishes two
    // boxes.
    tr.innerHTML = `
        <td>${image}</td>
        <td>
          <p class="has-text-weight-medium">${escapeHtml(product.name)}</p>
          <p class="is-size-7 has-text-grey">
            ${escapeHtml(product.type.name)}
            ${product.collection ? ` · ${escapeHtml(product.collection.name)}` : ""}
          </p>
        </td>
        <td>${colours}</td>
        <td>${photoCell(product)}</td>
        <td class="dash-col-actions">
          <span class="dash-row-actions is-flex is-gap-1">
            <button class="button is-small is-ghost" data-product-action="edit"
                    data-product-id="${product.id}" title="Editar" aria-label="Editar ${escapeHtml(product.name)}">
              <span class="icon"><i class="fa-solid fa-pencil"></i></span>
            </button>
            <button class="button is-small is-ghost has-text-danger" data-product-action="delete"
                    data-product-id="${product.id}" title="Apagar" aria-label="Apagar ${escapeHtml(product.name)}">
              <span class="icon"><i class="fa-solid fa-trash"></i></span>
            </button>
          </span>
        </td>`;

    return tr;
};

const renderProducts = (products) => {
    productList.innerHTML = "";

    // The subtitle carries the one figure worth knowing before you read a row,
    // and it is set on every path: leaving it at its placeholder made an empty
    // filtered list look like a page that had failed to load.
    const count = document.getElementById("product-count");
    const total = products?.length ?? 0;
    const pieces = `${total} ${total === 1 ? "peça" : "peças"}`;

    if (!total) {
        count.textContent = pieces;
        return renderEmptyMessage();
    }

    products.forEach((product) => productList.appendChild(row(product)));

    const missing = products.filter((p) => photoCount(p) === 0).length;
    count.innerHTML = missing
        ? `${pieces} · <span class="has-text-weight-medium"
             style="color: var(--ccg-attention)">${missing} sem fotografia</span>`
        : pieces;
};

/** Bulma's own skeleton, one row per record the table is about to hold. */
const renderSkeleton = () => {
    productList.innerHTML = `
        <tr><td colspan="${COLUMNS}" class="skeleton-block"></td></tr>`.repeat(6);
};

export const fetchProducts = async () => {
    renderSkeleton();
    try {
        // The query carries limit=100 plus whatever the filter bar has set.
        // The API defaults to 10, which silently hid four of fourteen products.
        const { products } = await request(`${API.products.list}?${query()}`,
                                          { fallback: "Erro ao buscar produtos." });

        // No endpoint filters on photographs, so it is applied here.
        const wanted = photoFilter();
        const visible = wanted
            ? products.filter((p) =>
                  wanted === "none" ? photoCount(p) === 0 : photoCount(p) > 0)
            : products;

        renderProducts(visible);
    } catch (error) {
        Notify.error("Erro ao buscar produtos");
        console.error("Error fetching products:", error);
    }
};
