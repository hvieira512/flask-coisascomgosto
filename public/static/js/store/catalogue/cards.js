import { ColorSet } from "../color-set.js";
import { ProductPlaceholder } from "../placeholder.js";
import { escapeHtml } from "../../core/html.js";

// Two names fill a card's width, so the third badge and the count share the
// second line rather than leaving a lone "+3" under a full row.
const MAX_BADGES = 3;

function renderColourways(product) {
    const sets = product.variants.map((variant) => variant.color_set).filter(Boolean);
    if (!sets.length) return "";

    const shown = sets.slice(0, MAX_BADGES).map((set) => ColorSet.badge(set)).join("");
    const rest = sets.length - MAX_BADGES;
    const more = rest > 0 ? `<span class="color-set-more">+${rest}</span>` : "";

    return `<span class="d-flex flex-wrap align-items-center gap-1 lh-1">${shown}${more}</span>`;
}

// align-content-start on the card: a grid item is stretched to its row's height
// and spreads the extra into its implicit rows, so a piece whose name takes two
// lines made every photograph in that row taller.
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
