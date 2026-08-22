export const ProductPlaceholder = (function () {
    const DEFAULT_COLOR = "#4472C4";
    const DEFAULT_ICON = "fa-gift";

    const iconFor = (product) => product.type?.icon || DEFAULT_ICON;

    function luminance(hex) {
        const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
        if (!match) return 255;

        const value = parseInt(match[1], 16);
        return 0.299 * ((value >> 16) & 255)
             + 0.587 * ((value >> 8) & 255)
             + 0.114 * (value & 255);
    }

    function colorFor(product, colorSet = null) {
        const set = colorSet || (product.variants || [])[0]?.color_set;
        const colors = (set?.colors || [])
            .map((c) => c.hex)
            .filter(Boolean);

        if (!colors.length) return DEFAULT_COLOR;

        const darkest = colors.reduce((a, b) =>
            luminance(b) < luminance(a) ? b : a
        );
        return luminance(darkest) > 210 ? DEFAULT_COLOR : darkest;
    }

    function tint(hex, alpha) {
        const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
        if (!match) return hex;

        const value = parseInt(match[1], 16);
        const r = (value >> 16) & 255;
        const g = (value >> 8) & 255;
        const b = value & 255;
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    function markup(product, extraClass = "", colorSet = null) {
        const color = colorFor(product, colorSet);
        const icon = iconFor(product);
        const subject = colorSet
            ? `${product.name} em ${colorSet.name}`
            : product.name;

        return `
          <div class="product-placeholder ${extraClass}"
               style="--ph-color:${color};
                      --ph-wash:${tint(color, 0.1)};
                      --ph-circle:${tint(color, 0.18)}"
               role="img"
               aria-label="${subject} — sem fotografia">
            <span class="disc product-placeholder-circle">
              <i class="fa-solid ${icon}"></i>
            </span>
          </div>`;
    }

    return { markup };
})();
