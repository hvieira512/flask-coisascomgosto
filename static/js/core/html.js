/**
 * Escaping for the template literals that build markup.
 *
 * A global rather than a module export because both kinds of script need it:
 * the dashboard's ES modules, and the classic scripts (color-set.js,
 * placeholder.js) that publish components on window. Every base template loads
 * this first. Seven files had their own byte-identical copy.
 */
window.escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[char]));
