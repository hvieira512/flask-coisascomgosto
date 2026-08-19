/**
 * Event dates and event state, in one place.
 *
 * Both the panel on Início and the table on Eventos show the same fair, and when
 * each worked it out for itself they disagreed: one called a fair that had
 * already opened "Por abrir" while the other called it "A decorrer".
 */

/** Explicit, because pt-PT's own short month renders as a number in Chrome. */
const MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

const parse = (iso) => new Date(`${iso}T00:00:00`);
const midnight = () => new Date(new Date().toDateString());

/** "7 Ago 2026" */
export function shortDate(iso) {
    const date = parse(iso);
    return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
}

/** "7 – 23 Ago 2026", collapsing the parts the two ends share. */
export function eventDates(event) {
    if (!event.ends_on || event.ends_on === event.starts_on) {
        return shortDate(event.starts_on);
    }

    const from = parse(event.starts_on);
    const to = parse(event.ends_on);

    if (from.getMonth() === to.getMonth() && from.getFullYear() === to.getFullYear()) {
        return `${from.getDate()} – ${to.getDate()} ${MONTHS[to.getMonth()]} ${to.getFullYear()}`;
    }
    if (from.getFullYear() === to.getFullYear()) {
        return `${from.getDate()} ${MONTHS[from.getMonth()]} – ${shortDate(event.ends_on)}`;
    }
    return `${shortDate(event.starts_on)} – ${shortDate(event.ends_on)}`;
}

/** "running" | "upcoming" | "past", against today. */
export function eventState(event) {
    const today = midnight();
    if (parse(event.ends_on || event.starts_on) < today) return "past";
    return parse(event.starts_on) <= today ? "running" : "upcoming";
}

/** Whole days until it opens; 0 or less once it has. */
export function daysUntil(event) {
    return Math.round((parse(event.starts_on) - midnight()) / 86400000);
}

export function stateChip(event, { extraClass = "" } = {}) {
    const state = eventState(event);
    if (state === "past") return "";

    const [tone, label] = state === "running"
        ? ["is-ready", "A decorrer"]
        : ["is-quiet", "Por abrir"];

    return `<span class="badge rounded-pill chip ${tone} ${extraClass}">${label}</span>`;
}
