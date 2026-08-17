/**
 * Bulma modals: a modal is open when it carries .is-active, and both dashboard
 * pages fill the same two slots. `submitting` wraps the button handlers.
 */
export const modal = (id) => document.getElementById(id);
export const bodyOf = (id) => modal(id).querySelector(".modal-card-body");
export const footOf = (id) => modal(id).querySelector(".modal-card-foot");
export const open = (id) => modal(id).classList.add("is-active");
export const close = (id) => modal(id).classList.remove("is-active");

/**
 * Run a click handler with the button spinning, surfacing any failure as a
 * toast. The button is captured before the first await deliberately: the
 * browser nulls event.currentTarget once dispatch ends, so an async handler
 * reading it after awaiting throws in its own finally block.
 */
export async function submitting(button, work) {
    button.classList.add("is-loading");
    try {
        await work();
    } catch (error) {
        Notify.error(error.message);
    } finally {
        button.classList.remove("is-loading");
    }
}
