/**
 * Filter state for the catalog page.
 *
 * Holds the selected filters, keeps them in the URL query string so a filtered
 * view is shareable and survives a reload, and renders two views of the same
 * state: the sidebar (active entries highlighted) and the badge row (one Bulma
 * delete-tag per active filter, removable by clicking the tag).
 */
window.StoreFilters = (function () {
    /** Filters that map straight onto /api/products query parameters. */
    const GROUPS = {
        q: { label: "Pesquisa" },
        material_id: { label: "Material" },
        type_id: { label: "Tipo" },
        collection_id: { label: "Colecção" },
    };

    const state = {};
    /** id -> display name, so a badge can show "Categoria: Madeira". */
    const labels = {};
    const listeners = [];

    function readFromUrl() {
        const params = new URLSearchParams(window.location.search);
        Object.keys(GROUPS).forEach((key) => {
            const value = params.get(key);
            if (value) state[key] = value;
        });
    }

    function writeToUrl() {
        const params = new URLSearchParams();
        Object.entries(state).forEach(([key, value]) => {
            if (value) params.set(key, value);
        });

        const query = params.toString();
        window.history.replaceState(
            null,
            "",
            query ? `${window.location.pathname}?${query}` : window.location.pathname
        );
    }

    function notify() {
        writeToUrl();
        listeners.forEach((fn) => fn(active()));
    }

    /** Only the filters that are actually set. */
    function active() {
        return Object.fromEntries(
            Object.entries(state).filter(([, value]) => value !== "" && value != null)
        );
    }

    function set(group, value, label) {
        if (!(group in GROUPS)) return;

        if (value === null || value === undefined || value === "") {
            delete state[group];
        } else {
            state[group] = String(value);
            if (label) labels[`${group}:${value}`] = label;
        }
        notify();
    }

    /** Toggle a value off if it is already the selected one. */
    function toggle(group, value, label) {
        set(group, state[group] === String(value) ? null : value, label);
    }

    function clear(group) {
        set(group, null);
    }

    function clearAll() {
        Object.keys(state).forEach((key) => delete state[key]);
        notify();
    }

    function labelFor(group, value) {
        if (group === "q") return value;
        return labels[`${group}:${value}`] || `#${value}`;
    }

    function get(group) {
        return state[group];
    }

    function onChange(fn) {
        listeners.push(fn);
    }

    /** Register a display name discovered while rendering the sidebar. */
    function registerLabel(group, value, label) {
        labels[`${group}:${value}`] = label;
    }

    readFromUrl();

    return {
        GROUPS,
        active,
        set,
        toggle,
        clear,
        clearAll,
        get,
        labelFor,
        registerLabel,
        onChange,
    };
})();
