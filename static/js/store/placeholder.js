// No-photo tile: a wash of the product's own colour behind its type icon.
export const ProductPlaceholder = (function () {
    /** Brand blue, used when a product has no colour of its own. */
    const DEFAULT_COLOR = "#4472C4";
    const DEFAULT_ICON = "fa-gift";

    /** The API resolves this — the type's own icon, or one guessed from its name
     *  by api/type_icons.py. There used to be a second copy of that keyword table
     *  here, kept in step by a comment. */
    const iconFor = (product) => product.type?.icon || DEFAULT_ICON;

    /** Perceived brightness, 0–255. */
    function luminance(hex) {
        const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
        if (!match) return 255;

        const value = parseInt(match[1], 16);
        return 0.299 * ((value >> 16) & 255)
             + 0.587 * ((value >> 8) & 255)
             + 0.114 * (value & 255);
    }

    /**
     * The darkest colour in the set, not the first.
     *
     * Most sets pair a light body with a darker motif ("Branco e Dourado"), and
     * the tile draws the icon in this colour over a 10% wash of it — so taking
     * the first colour painted white-on-white and the icon vanished.
     *
     * `colorSet` names which set to draw; without one the product's first
     * variant stands for the piece as a whole.
     */
    function colorFor(product, colorSet = null) {
        const set = colorSet || (product.variants || [])[0]?.color_set;
        const colors = (set?.colors || [])
            .map((c) => c.hex)
            .filter(Boolean);

        if (!colors.length) return DEFAULT_COLOR;

        const darkest = colors.reduce((a, b) =>
            luminance(b) < luminance(a) ? b : a
        );
        // Still too pale to read against its own wash.
        return luminance(darkest) > 210 ? DEFAULT_COLOR : darkest;
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

    /**
     * `colorSet` tints the tile for one particular colour rather than for the
     * piece as a whole, so that stepping through a product's colours changes the
     * tile even where none of them has been photographed yet.
     */
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
