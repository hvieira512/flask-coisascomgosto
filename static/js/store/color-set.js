/**
 * Renders a colour set as a rounded badge: its overlapping colour circles and
 * the set's name, drawn in its first colour on a pale wash of the same.
 *
 * Shared by the catalog cards and the product page's variant buttons so the two
 * cannot drift apart.
 */
window.ColorSet = (function () {
    const FALLBACK = "#4472C4";
    /** Above this, a colour is too light to read as text on its own wash. */
    const MAX_TEXT_LUMINANCE = 140;

    function rgb(hex) {
        const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
        if (!match) return null;
        const value = parseInt(match[1], 16);
        return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
    }

    function luminance([r, g, b]) {
        return 0.299 * r + 0.587 * g + 0.114 * b;
    }

    /** Scales a colour down until it is dark enough to read. */
    function readable(channels) {
        let current = channels;
        while (luminance(current) > MAX_TEXT_LUMINANCE) {
            current = current.map((c) => Math.round(c * 0.82));
        }
        return current;
    }

    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, (c) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        }[c]));
    }

    /** The inline custom properties the .color-set-badge rule paints with. */
    function style(colorSet) {
        const channels = rgb((colorSet.colors || [])[0]?.hex) || rgb(FALLBACK);
        const [r, g, b] = channels;
        const [tr, tg, tb] = readable(channels);

        return `--cs-bg:rgba(${r},${g},${b},.14);` +
               `--cs-border:rgba(${r},${g},${b},.32);` +
               `--cs-fg:rgb(${tr},${tg},${tb})`;
    }

    /** The overlapping circles, one per colour. */
    function dots(colorSet) {
        const colors = (colorSet.colors || []).filter((c) => c.hex);
        if (!colors.length) return "";

        const circles = colors
            .map((c) => `<span class="swatch" style="background:${escapeHtml(c.hex)}"></span>`)
            .join("");
        return `<span class="swatch-set">${circles}</span>`;
    }

    function badge(colorSet, extraClass = "") {
        if (!colorSet) return "";
        return `<span class="tag is-rounded color-set-badge ${extraClass}"
                      title="${escapeHtml(colorSet.name)}"
                      style="${style(colorSet)}">${dots(colorSet)}<span class="color-set-name">${escapeHtml(colorSet.name)}</span></span>`;
    }

    return { badge, dots, style };
})();
