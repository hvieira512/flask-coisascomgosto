import { escapeHtml } from "../core/html.js";

export const ColorSet = (function () {
    const FALLBACK = "#4472C4";
    const MIN_CONTRAST = 4.5;
    const PAPER = [250, 248, 245];
    const WASH_ALPHA = 0.14;

    function rgb(hex) {
        const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
        if (!match) return null;
        const value = parseInt(match[1], 16);
        return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
    }

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

    function inkFor(colours) {
        return colours.reduce((darkest, c) =>
            relativeLuminance(c) < relativeLuminance(darkest) ? c : darkest
        );
    }

    function readable(channels, wash) {
        let current = channels;
        for (let i = 0; i < 40 && contrast(current, wash) < MIN_CONTRAST; i += 1) {
            current = current.map((c) => Math.round(c * 0.86));
        }
        return current;
    }

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
        return `<span class="color-set-badge ${extraClass}"
                      title="${escapeHtml(colorSet.name)}"
                      style="${style(colorSet)}">${dots(colorSet)}<span class="color-set-name">${escapeHtml(colorSet.name)}</span></span>`;
    }

    return { badge, dots, style };
})();
