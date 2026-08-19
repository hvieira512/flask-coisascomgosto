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
export const bodyOf = (id) => modal(id).querySelector(".modal-body");
export const footOf = (id) => modal(id).querySelector(".modal-footer");

export const open = (id) => {
    const dialog = modal(id);
    if (!dialog || dialog.open) return;

    dialog.showModal();
    // The browser focuses the first focusable thing, which is the × — leaving
    // Enter wired to "close the dialog I have just opened". A form dialog starts
    // in its first field instead; one with no fields keeps the default.
    dialog.querySelector(".modal-body :is(input, textarea, select)")?.focus();
};

export const close = (id) => {
    const dialog = modal(id);
    if (dialog?.open) dialog.close();
};

/**
 * A dialog whose body is a form.
 *
 * Tipos and Eventos were each writing this out: fill the body, add the same two
 * buttons, wire the primary one through `submitting`, close, toast, reload the
 * table behind it. Only the body, the labels and the save itself differ.
 *
 * `afterRender` is for a form that has to wire something of its own — the type
 * form previews the icon you pick.
 */
export function formDialog({ id, body, submitLabel, onSubmit, success, after, afterRender }) {
    bodyOf(id).innerHTML = body;
    footOf(id).innerHTML = `
        <button class="btn btn-outline-secondary" data-modal-close>Cancelar</button>
        <button class="btn btn-dark" data-dialog-submit>${submitLabel}</button>`;
    open(id);
    afterRender?.(modal(id));

    modal(id).querySelector("[data-dialog-submit]").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            const result = await onSubmit(modal(id));
            close(id);
            if (success) Notify.success(success);
            await after?.(result);
        });
}

/** The same shape for "are you sure", with the destructive button. */
export function confirmDialog({ id, body, confirmLabel = "Apagar", onConfirm, success, after }) {
    bodyOf(id).innerHTML = body;
    footOf(id).innerHTML = `
        <button class="btn btn-outline-secondary" data-modal-close>Cancelar</button>
        <button class="btn btn-danger" data-dialog-confirm>${confirmLabel}</button>`;
    open(id);

    modal(id).querySelector("[data-dialog-confirm]").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            await onConfirm();
            close(id);
            if (success) Notify.success(success);
            await after?.();
        });
}

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
