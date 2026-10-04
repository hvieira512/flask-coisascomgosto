export const StoreFilters = (function () {
    const GROUPS = {
        q: { label: "Pesquisa", multiple: false },
        material_id: { label: "Material", multiple: true },
        type_id: { label: "Tipo", multiple: true },
        collection_id: { label: "Colecção", multiple: true },
    };

    const state = {};
    const labels = {};
    const listeners = [];

    const isMultiple = (group) => Boolean(GROUPS[group]?.multiple);

    function readFromUrl() {
        const params = new URLSearchParams(window.location.search);
        Object.keys(GROUPS).forEach((key) => {
            if (isMultiple(key)) {
                const values = params.getAll(key).filter(Boolean);
                if (values.length) state[key] = values;
            } else {
                const value = params.get(key);
                if (value) state[key] = value;
            }
        });
    }

    function writeToUrl() {
        const params = new URLSearchParams();
        Object.entries(state).forEach(([key, value]) => {
            if (Array.isArray(value)) value.forEach((v) => params.append(key, v));
            else if (value) params.set(key, value);
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

    function active() {
        return Object.fromEntries(
            Object.entries(state).filter(([, value]) =>
                Array.isArray(value) ? value.length > 0 : value !== "" && value != null
            )
        );
    }

    function selections() {
        return Object.keys(GROUPS).flatMap((group) => {
            const value = state[group];
            if (!value) return [];
            return (Array.isArray(value) ? value : [value]).map((v) => ({
                group,
                value: v,
            }));
        });
    }

    function isSelected(group, value) {
        const current = state[group];
        if (!current) return false;
        return Array.isArray(current)
            ? current.includes(String(value))
            : current === String(value);
    }

    function set(group, value, label) {
        if (!(group in GROUPS)) return;

        if (value === null || value === undefined || value === "") {
            delete state[group];
        } else {
            state[group] = isMultiple(group) ? [String(value)] : String(value);
            if (label) labels[`${group}:${value}`] = label;
        }
        notify();
    }

    function toggle(group, value, label) {
        if (!(group in GROUPS)) return;

        if (!isMultiple(group)) {
            set(group, isSelected(group, value) ? null : value, label);
            return;
        }

        const wanted = String(value);
        const current = state[group] ?? [];
        const next = current.includes(wanted)
            ? current.filter((v) => v !== wanted)
            : [...current, wanted];

        if (next.length) state[group] = next;
        else delete state[group];

        if (label) labels[`${group}:${wanted}`] = label;
        notify();
    }

    function clear(group, value = null) {
        if (value === null || !isMultiple(group)) {
            delete state[group];
            notify();
            return;
        }

        const next = (state[group] ?? []).filter((v) => v !== String(value));
        if (next.length) state[group] = next;
        else delete state[group];
        notify();
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

    function registerLabel(group, value, label) {
        labels[`${group}:${value}`] = label;
    }

    readFromUrl();

    return {
        GROUPS,
        active,
        selections,
        isSelected,
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
