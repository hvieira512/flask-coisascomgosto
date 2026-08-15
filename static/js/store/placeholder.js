// No-photo tile: a wash of the product's own colour behind its type icon.
// The keyword table is mirrored by the `type_icon` filter in web/filters.py.
window.ProductPlaceholder = (function () {
    /** Brand blue, used when a product has no colour of its own. */
    const DEFAULT_COLOR = "#4472C4";
    const DEFAULT_ICON = "fa-gift";

    // First match wins.
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

        const names = [type?.name, type?.parent?.name].filter(Boolean).join(" ");
        const match = KEYWORD_ICONS.find(([pattern]) => pattern.test(names));
        return match ? match[1] : DEFAULT_ICON;
    }

    function colorFor(product) {
        const variant = (product.variants || [])[0];
        return variant?.color_set?.colors?.[0]?.hex || DEFAULT_COLOR;
    }

    // Non-hex values pass through so a named colour still works.
    function tint(hex, alpha) {
        const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
        if (!match) return hex;

        const value = parseInt(match[1], 16);
        const r = (value >> 16) & 255;
        const g = (value >> 8) & 255;
        const b = value & 255;
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

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
