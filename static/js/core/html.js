/**
 * Escaping for the template literals that build markup.
 *
 * Seven files had their own byte-identical copy of this before it was shared.
 */
export const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[char]));
