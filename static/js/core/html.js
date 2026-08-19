/**
 * Escaping for the template literals that build markup.
 *
 * Seven files had their own byte-identical copy of this before it was shared.
 */
export const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[char]));

/**
 * The trailing icon of a form field, as Bootstrap's input group addon.
 *
 * Fields read [control][icon]: the control first, its icon attached after it.
 * Wrap the control and this together in `.input-group`:
 *
 *     <div class="input-group">
 *       <input class="form-control" id="ef-url">
 *       ${fieldIcon("fa-solid fa-link")}
 *     </div>
 *
 * `icon` is the full Font Awesome class rather than just the glyph, because the
 * brand marks (fa-brands fa-whatsapp) live in a different family from the solid
 * set and the caller is the only one that knows which it wants.
 *
 * Mirrors the field_icon macro in templates/dashboard/components/page.html, so
 * a field looks the same whether Jinja or the browser built it.
 */
export const fieldIcon = (icon) =>
    `<span class="input-group-text"><i class="${icon}" aria-hidden="true"></i></span>`;
