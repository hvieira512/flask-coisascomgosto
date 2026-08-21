import { ColorSet } from "../color-set.js";
import { ProductPlaceholder } from "../placeholder.js";
import { escapeHtml } from "../../core/html.js";

/** Three swatches and a count. Every colourway is on the piece's own page. */
const MAX_DOTS = 3;

function renderColourways(product) {
    const sets = product.variants.map((variant) => variant.color_set).filter(Boolean);
    if (!sets.length) return "";

    const shown = sets.slice(0, MAX_DOTS).map((set) => ColorSet.dot(set)).join("");
    const rest = sets.length - MAX_DOTS;
    const more = rest > 0
        ? `<span class="fs-7 font-monospace text-body-tertiary">+${rest}</span>`
        : "";

    return `<span class="dots d-flex align-items-center gap-1">${shown}${more}</span>`;
}

/**
 * One tile of the grid: the photograph, then the name and its family on a line,
 * then which colours the piece is made in.
 *
 * align-content-start is not decoration. A grid item is stretched to its row's
 * height and an item whose own rows are all implicit distributes that extra
 * height into them — so a piece whose name takes two lines made every
 * photograph in its row taller than the rest.
 */
export function productCard(product) {
    const image = product.primary_image;
    const media = image
        ? `<img class="object-fit-cover" src="${escapeHtml(image.url)}"
                alt="${escapeHtml(image.alt || product.name)}" loading="lazy">`
        : ProductPlaceholder.markup(product);

    return `
      <div class="col">
        <a class="d-grid align-content-start gap-2 h-100 text-decoration-none text-body product-card"
           href="/products/${product.id}">
          <span class="ratio d-block" style="--bs-aspect-ratio: 125%">${media}</span>

          <span class="d-flex align-items-baseline justify-content-between gap-2
                       border-top pt-2 product-card-line">
            <span class="h6 font-display mb-0">${escapeHtml(product.name)}</span>
            ${product.type?.name
                ? `<span class="fs-7 text-uppercase font-monospace text-body-tertiary text-nowrap">${escapeHtml(product.type.name)}</span>`
                : ""}
          </span>

          ${renderColourways(product)}
        </a>
      </div>`;
}
