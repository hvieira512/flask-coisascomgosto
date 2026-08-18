/**
 * Native <dialog> modals. Every dashboard page fills the same two slots, and
 * `submitting` wraps the button handlers.
 *
 * showModal() is what buys the focus trap, Escape, the backdrop and returning
 * focus to whatever opened it; the enter and leave animations are CSS. Calling
 * it on an already-open dialog throws, hence the guards.
 */

import { Notify } from "./notify.js";

export const modal = (id) => document.getElementById(id);
export const bodyOf = (id) => modal(id).querySelector(".modal-card-body");
export const footOf = (id) => modal(id).querySelector(".modal-card-foot");

export const open = (id) => {
    const dialog = modal(id);
    if (!dialog || dialog.open) return;

    dialog.showModal();
    // The browser focuses the first focusable thing, which is the × — leaving
    // Enter wired to "close the dialog I have just opened". A form dialog starts
    // in its first field instead; one with no fields keeps the default.
    dialog.querySelector(".modal-card-body :is(input, textarea, select)")?.focus();
};

export const close = (id) => {
    const dialog = modal(id);
    if (dialog?.open) dialog.close();
};

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
