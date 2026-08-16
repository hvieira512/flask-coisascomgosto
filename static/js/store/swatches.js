/**
 * Renders a colour set as one tight circle per colour.
 *
 * Shared by the catalog cards and the product page's variant buttons so the
 * two cannot drift apart.
 */
window.Swatches = (function () {
    const FALLBACK = "#DDD";

    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, (c) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        }[c]));
    }

    function render(colorSet) {
        const colors = (colorSet && colorSet.colors) || [];
        if (!colors.length) return "";

        const dots = colors
            .map((c) => `<span class="swatch" style="background:${escapeHtml(c.hex || FALLBACK)}"></span>`)
            .join("");

        return `<span class="swatch-set" title="${escapeHtml(colorSet.name)}">${dots}</span>`;
    }

    return { render };
})();
