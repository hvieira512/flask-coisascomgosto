export const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[char]));

export const fieldIcon = (icon) =>
    `<span class="input-group-text"><i class="${icon}" aria-hidden="true"></i></span>`;
