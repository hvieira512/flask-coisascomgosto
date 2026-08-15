/**
 * Placeholder tile for products that have no photograph yet.
 *
 * Rather than a grey box, it borrows the product's own identity: a pale wash of
 * its first variant colour, and a Font Awesome icon for its product type sitting
 * in a paler circle. The icon itself is drawn in the full colour so it reads
 * against the wash.
 *
 * The Jinja macro in templates/store/components/placeholder.html renders the
 * same thing server-side; keep the two in step.
 */
window.ProductPlaceholder = (function () {
    /** Brand blue, used when a product has no colour of its own. */
    const DEFAULT_COLOR = "#4472C4";
    const DEFAULT_ICON = "fa-gift";

    /**
     * Guess an icon from the type name when the type has none set.
     * Owners can override any of this by setting `icon` on the product type.
     */
    const KEYWORD_ICONS = [
        [/cora[çc][ãa]o|heart/i, "fa-heart"],
        [/moldura|quadro|frame|foto/i, "fa-image"],
        [/bastidor|hoop/i, "fa-circle-notch"],
        [/escova|brush|cabelo/i, "fa-brush"],
        [/redond|circul|round/i, "fa-circle-dot"],
        [/caixa|box|estojo/i, "fa-box"],
        [/len[çc]o|pano|tecido|cloth/i, "fa-scroll"],
        [/[íi]man|magnet/i, "fa-magnet"],
        [/chave|key/i, "fa-key"],
    ];

    function iconFor(product) {
        const type = product.type;
        if (type?.icon) return type.icon;

        // A sub-type inherits its parent's icon; the API already resolves that,
        // but fall back to matching either name here too.
        const names = [type?.name, type?.parent?.name].filter(Boolean).join(" ");
        const match = KEYWORD_ICONS.find(([pattern]) => pattern.test(names));
        return match ? match[1] : DEFAULT_ICON;
    }

    /** The product's identifying colour: the first colour of its first variant. */
    function colorFor(product) {
        const variant = (product.variants || [])[0];
        return variant?.color_set?.colors?.[0]?.hex || DEFAULT_COLOR;
    }

    /**
     * Turn #RRGGBB into an rgba() string.
     * Non-hex values are returned untouched so a named colour still works.
     */
    function tint(hex, alpha) {
        const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
        if (!match) return hex;

        const value = parseInt(match[1], 16);
        const r = (value >> 16) & 255;
        const g = (value >> 8) & 255;
        const b = value & 255;
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    /** Markup for the tile. `extraClass` lets callers match their own sizing. */
    function markup(product, extraClass = "") {
        const color = colorFor(product);
        const icon = iconFor(product);

        return `
          <div class="product-placeholder ${extraClass}"
               style="--ph-color:${color};
                      --ph-wash:${tint(color, 0.1)};
                      --ph-circle:${tint(color, 0.18)}"
               role="img"
               aria-label="${product.name} — sem fotografia">
            <span class="product-placeholder-circle">
              <i class="fa-solid ${icon}"></i>
            </span>
          </div>`;
    }

    return { markup, iconFor, colorFor, tint };
})();
