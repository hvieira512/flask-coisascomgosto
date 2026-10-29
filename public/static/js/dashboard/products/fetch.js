import { API, request } from "../../core/api.js";
import { ColorSet } from "../../store/color-set.js";
import { Notify } from "../../core/notify.js";
import { ProductPlaceholder } from "../../store/placeholder.js";
import { escapeHtml } from "../../core/html.js";
import { filterParams, isFiltered, photoFilter } from "./filters.js";

const productList = document.getElementById("product-list");
const COLUMNS = 5;

const renderEmptyMessage = () => {
    const filtered = isFiltered();
    productList.innerHTML = `
        <tr>
          <td colspan="${COLUMNS}" class="text-center py-5">
            <span class="text-body-tertiary">
              <i class="fa-solid ${filtered ? "fa-filter-circle-xmark" : "fa-box-open"} fa-2x"></i>
            </span>
            <p class="mt-3 text-body-secondary">
              ${filtered
                  ? "Nenhuma peça corresponde aos filtros."
                  : "Ainda não há peças no catálogo."}
            </p>
          </td>
        </tr>`;
};

const photoCount = (product) =>
    (product.images ?? []).length
    + product.variants.reduce((n, v) => n + (v.images ?? []).length, 0);

const photoCell = (product) => {
    const photos = photoCount(product);
    if (photos === 0) {
        return `<span class="badge rounded-pill chip is-attention d-inline-flex align-items-center gap-1">
                  <span class="icon is-small"><i class="fa-solid fa-triangle-exclamation"></i></span>
                  <span>Sem fotografia</span>
                </span>`;
    }
    return `<span class="data text-body-secondary">${photos} ${photos === 1 ? "foto" : "fotos"}</span>`;
};

const row = (product) => {
    const tr = document.createElement("tr");
    tr.dataset.productId = product.id;

    const image = product.primary_image
        ? `<img class="dash-thumb" src="${escapeHtml(product.primary_image.url)}"
                alt="${escapeHtml(product.name)}">`
        : ProductPlaceholder.markup(product);

    const SHOWN = 3;
    const shown = product.variants.slice(0, SHOWN);
    const rest = product.variants.length - shown.length;

    const colours = product.variants.length
        ? `<span class="d-flex align-items-center gap-1">
             ${shown.map((v) => ColorSet.badge(v.color_set)).join("")}
             ${rest ? `<span class="data text-body-secondary">+${rest}</span>` : ""}
           </span>`
        : `<span class="badge rounded-pill chip is-quiet">Sem cores</span>`;

    tr.innerHTML = `
        <td class="dash-col-thumb">${image}</td>
        <td class="dash-col-name">
          <p class="fw-medium mb-0">${escapeHtml(product.name)}</p>
          <p class="fs-7 text-body-secondary mb-0">
            ${escapeHtml(product.type.name)}
            ${product.collections.length
                ? ` · ${escapeHtml(product.collections.map((c) => c.name).join(", "))}`
                : ""}
          </p>
        </td>
        <td>${colours}</td>
        <td class="dash-col-photos" data-label="Fotografias">${photoCell(product)}</td>
        <td class="dash-col-actions">
          <span class="dash-row-actions d-flex gap-1">
            <button class="btn btn-sm btn-ghost" data-product-action="edit"
                    data-product-id="${product.id}" title="Editar" aria-label="Editar ${escapeHtml(product.name)}">
              <span class="icon"><i class="fa-solid fa-pencil"></i></span>
            </button>
            <button class="btn btn-sm btn-ghost text-danger" data-product-action="delete"
                    data-product-id="${product.id}" title="Apagar" aria-label="Apagar ${escapeHtml(product.name)}">
              <span class="icon"><i class="fa-solid fa-trash"></i></span>
            </button>
          </span>
        </td>`;

    return tr;
};

const renderCount = (total, missing) => {
    const pieces = `${total} ${total === 1 ? "peça" : "peças"}`;
    document.getElementById("product-count").innerHTML = missing
        ? `${pieces} · <span class="fw-medium"
             style="color: var(--ccg-attention)">${missing} sem fotografia</span>`
        : pieces;
};

const renderPager = ({ page, pages }) => {
    document.getElementById("product-pager").hidden = pages <= 1;
    document.getElementById("pager-label").textContent = `Página ${page} de ${pages}`;
    document.getElementById("pager-prev").disabled = page <= 1;
    document.getElementById("pager-next").disabled = page >= pages;
};

const renderProducts = (products) => {
    productList.classList.remove("is-loading");
    productList.innerHTML = "";
    if (!products.length) return renderEmptyMessage();

    products.forEach((product) => productList.appendChild(row(product)));
};

// While a request is out, the rows already on screen stay and dim; only an
// empty table gets placeholder rows, so a filter never flashes a bare grid.
const renderSkeleton = () => {
    if (productList.children.length) {
        productList.classList.add("is-loading");
        return;
    }
    productList.innerHTML = `
        <tr>
          <td colspan="${COLUMNS}" class="placeholder-glow">
            <span class="placeholder w-100"></span>
          </td>
        </tr>`.repeat(6);
};

// Pages rather than the whole catalogue: a list of every piece stopped being
// possible at the API's hundred-row limit.
const PAGE_SIZE = 50;
let currentPage = 1;
let latest = 0;

/** How many of the filtered pieces have no photograph, asked of the server. */
const countMissing = async (total) => {
    if (photoFilter() === "none") return total;
    if (photoFilter() === "some") return 0;

    const { pagination } = await request(API.products.list, {
        params: { ...filterParams({ photos: "none" }), limit: 1 },
        partial: true,
    });
    return pagination.total;
};

/** Page `page` of the filtered pieces; a filter change asks for page 1, a save for the same page. */
export const fetchProducts = async (page = currentPage) => {
    // A filter changed while the previous fetch was still counting: whatever
    // that fetch still has to say is about a list nobody is looking at anymore.
    const call = ++latest;
    currentPage = page;
    renderSkeleton();
    try {
        const { products, pagination } = await request(API.products.list, {
            params: { ...filterParams(), page, limit: PAGE_SIZE },
            fallback: "Erro ao buscar peças.",
        });
        if (call !== latest) return;

        // The last piece of the last page was deleted: show the page before.
        if (!products.length && page > 1) return fetchProducts(Math.max(1, pagination.pages));

        renderProducts(products);
        renderPager(pagination);
        const missing = await countMissing(pagination.total);
        if (call !== latest) return;
        renderCount(pagination.total, missing);
    } catch (error) {
        productList.classList.remove("is-loading");
        Notify.error("Erro ao buscar peças");
        console.error("Error fetching products:", error);
    }
};

document.getElementById("pager-prev")?.addEventListener("click", () => fetchProducts(currentPage - 1));
document.getElementById("pager-next")?.addEventListener("click", () => fetchProducts(currentPage + 1));
