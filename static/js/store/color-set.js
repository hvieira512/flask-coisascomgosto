/**
 * Renders a colour set as a rounded badge: its overlapping colour circles and
 * the set's name, drawn in its first colour on a pale wash of the same.
 *
 * Shared by the catalog cards and the product page's variant buttons so the two
 * cannot drift apart.
 */
window.ColorSet = (function () {
    const FALLBACK = "#4472C4";
    /** WCAG AA for body text, which is what a badge's name is. */
    const MIN_CONTRAST = 4.5;
    /** --ccg-paper, the ground the wash is composited over. */
    const PAPER = [250, 248, 245];
    const WASH_ALPHA = 0.14;

    function rgb(hex) {
        const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
        if (!match) return null;
        const value = parseInt(match[1], 16);
        return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
    }

    /** WCAG relative luminance, not the perceived-brightness approximation:
     *  the contrast ratio below is only meaningful against this one. */
    function relativeLuminance([r, g, b]) {
        const channel = (c) => {
            const v = c / 255;
            return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
        };
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
    }

    function contrast(a, b) {
        const [hi, lo] = [relativeLuminance(a), relativeLuminance(b)].sort((x, y) => y - x);
        return (hi + 0.05) / (lo + 0.05);
    }

    const over = (channels, alpha, ground) =>
        channels.map((c, i) => c * alpha + ground[i] * (1 - alpha));

    /**
     * The set's darkest colour, not its first.
     *
     * "Branco e Dourado" led with white, which had to be darkened so far to be
     * readable that the badge came out grey — the name of a gold piece printed in
     * grey, at 3.4:1 against its own wash. The darkest colour is the one that can
     * carry the text and still say which set this is.
     */
    function inkFor(colours) {
        return colours.reduce((darkest, c) =>
            relativeLuminance(c) < relativeLuminance(darkest) ? c : darkest
        );
    }

    /** Scales a colour down until it reads against the wash behind it. */
    function readable(channels, wash) {
        let current = channels;
        // Bounded: 0.86^40 is black long before it runs out.
        for (let i = 0; i < 40 && contrast(current, wash) < MIN_CONTRAST; i += 1) {
            current = current.map((c) => Math.round(c * 0.86));
        }
        return current;
    }

    /** The inline custom properties the .color-set-badge rule paints with. */
    function style(colorSet) {
        const colours = (colorSet.colors || [])
            .map((c) => rgb(c.hex))
            .filter(Boolean);
        const identity = colours[0] || rgb(FALLBACK);
        const ink = colours.length ? inkFor(colours) : rgb(FALLBACK);

        const [r, g, b] = identity;
        const [br, bg, bb] = ink;
        const wash = over(identity, WASH_ALPHA, PAPER);
        const [tr, tg, tb] = readable(ink, wash);

        return `--cs-bg:rgba(${r},${g},${b},.14);` +
               `--cs-border:rgba(${br},${bg},${bb},.32);` +
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
