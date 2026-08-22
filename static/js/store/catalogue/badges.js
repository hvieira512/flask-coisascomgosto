import { StoreFilters } from "../filters.js";
import { escapeHtml } from "../../core/html.js";

export function mountBadges(searchInput) {
    const row = document.getElementById("active-filters");
    const clearButton = document.getElementById("clear-filters");

    function remove(badge) {
        const { removeFilter: group, removeValue: value } = badge.dataset;
        StoreFilters.clear(group, value ?? null);
        if (group === "q") searchInput.value = "";
    }

    row.addEventListener("click", (event) => {
        const badge = event.target.closest("[data-remove-filter]");
        if (badge) remove(badge);
    });

    row.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;

        const badge = event.target.closest("[data-remove-filter]");
        if (!badge) return;

        event.preventDefault();
        remove(badge);
    });

    clearButton.addEventListener("click", () => {
        StoreFilters.clearAll();
        searchInput.value = "";
    });

    return {
        render() {
            const chosen = StoreFilters.selections();
            row.hidden = chosen.length === 0;
            clearButton.hidden = chosen.length === 0;

            row.innerHTML = chosen
                .map(({ group, value }) => {
                    const groupLabel = StoreFilters.GROUPS[group].label;
                    const valueLabel = StoreFilters.labelFor(group, value);
                    return `
                      <span class="filter-badge"
                            data-remove-filter="${group}" data-remove-value="${escapeHtml(value)}"
                            role="button" tabindex="0"
                            title="Remover ${escapeHtml(valueLabel)}">
                        ${escapeHtml(groupLabel)}: ${escapeHtml(valueLabel)}
                        <button class="btn-close btn-close-white"
                                aria-label="Remover ${escapeHtml(valueLabel)}"></button>
                      </span>`;
                })
                .join("");
        },
    };
}
