import { ColorSet } from "../color-set.js";
import { ProductPlaceholder } from "../placeholder.js";
import { escapeHtml } from "../../core/html.js";

/** Two rows of two. A fifth colour set added a third row to one card and
 *  left it taller than its neighbours; the rest are on the product page. */
const MAX_BADGES = 4;

function renderColorSets(product) {
    const sets = product.variants.map((variant) => variant.color_set).filter(Boolean);
    if (!sets.length) return "";

    const overflows = sets.length > MAX_BADGES;
    const visible = overflows ? MAX_BADGES - 1 : sets.length;
    const cells = sets.slice(0, visible).map(ColorSet.badge);

    if (overflows) {
        const rest = sets.length - visible;
        cells.push(
            `<span class="color-set-more">+${rest} ${rest === 1 ? "cor" : "cores"}</span>`
        );
    }

    return `<div class="swatch-row row row-cols-2 g-1">${
        cells.map((cell) => `<div class="col">${cell}</div>`).join("")
    }</div>`;
}

/** One tile of the grid: the photograph or its stand-in, the name, and what
 *  colours the piece is made in. */
export function productCard(product) {
    const image = product.primary_image;
    const media = image
        ? `<img class="card-img-top" src="${escapeHtml(image.url)}"
                alt="${escapeHtml(image.alt || product.name)}" loading="lazy">`
        : ProductPlaceholder.markup(product);

    const subtitle = [product.type?.name, product.collection?.name]
        .filter(Boolean)
        .map(escapeHtml)
        .join(" · ");

    return `
      <div class="col">
        <a class="card product-card" href="/products/${product.id}">
          ${media}
          <div class="card-body">
            <p class="h6 mb-1">${escapeHtml(product.name)}</p>
            ${subtitle ? `<p class="fs-7 text-body-secondary">${subtitle}</p>` : ""}
            ${renderColorSets(product)}
          </div>
        </a>
      </div>`;
}
