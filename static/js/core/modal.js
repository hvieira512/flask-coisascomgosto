/**
 * Bootstrap modals. Every dashboard page fills the same two slots, and
 * `submitting` wraps the button handlers.
 *
 * Bootstrap supplies the backdrop, the focus trap, Escape, the scroll lock and
 * the fade; `data-bs-dismiss="modal"` closes one without any code of ours. What
 * is left here is the part that is ours: the body has to be built before the
 * modal is any use, because a form needs the record it is editing.
 */

import { Notify } from "./notify.js";

export const modal = (id) => document.getElementById(id);
export const bodyOf = (id) => modal(id).querySelector(".modal-body");
export const footOf = (id) => modal(id).querySelector(".modal-footer");

const instance = (id) => bootstrap.Modal.getOrCreateInstance(modal(id));

/**
 * Resolves when a modal has finished opening.
 *
 * Bootstrap's hide() returns early while the 150ms show transition is still
 * running, so a save that finished inside that window left the form open with its
 * work already done — the owner pressed Guardar, the type was created, and the
 * dialog sat there as if nothing had happened.
 */
const opened = new WeakMap();

export const open = (id) => {
    const element = modal(id);
    if (!element) return;

    opened.set(element, new Promise((resolve) => {
        element.addEventListener("shown.bs.modal", resolve, { once: true });
    }));

    // The first field, not the ×, which would leave Enter wired to "close the
    // dialog I have just opened". Bootstrap focuses the modal itself on show, so
    // this has to wait for that to have happened.
    element.addEventListener("shown.bs.modal", () => {
        element.querySelector(".modal-body :is(input, textarea, select)")?.focus();
    }, { once: true });

    // Bootstrap keeps one backdrop and one scroll lock for all modals, so showing
    // a second while the first is still fading out leaves the page scrollable
    // behind it and the backdrop out of step. The create wizard hands over to the
    // edit modal exactly like that, so the handover waits.
    const other = [...document.querySelectorAll(".modal.show")]
        .find((open_) => open_ !== element);
    if (other) {
        other.addEventListener("hidden.bs.modal", () => instance(id).show(), { once: true });
        return;
    }

    instance(id).show();
};

export const close = async (id) => {
    const element = modal(id);
    if (!element) return;

    // `await undefined` resolves at once, so a modal nobody opened through open()
    // closes immediately.
    await opened.get(element);
    instance(id).hide();
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
        <button class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
        <button class="btn btn-dark" data-dialog-submit>${submitLabel}</button>`;
    open(id);
    afterRender?.(modal(id));

    modal(id).querySelector("[data-dialog-submit]").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            const result = await onSubmit(modal(id));
            await close(id);
            if (success) Notify.success(success);
            await after?.(result);
        });
}

/** The same shape for "are you sure", with the destructive button. */
export function confirmDialog({ id, body, confirmLabel = "Apagar", onConfirm, success, after }) {
    bodyOf(id).innerHTML = body;
    footOf(id).innerHTML = `
        <button class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
        <button class="btn btn-danger" data-dialog-confirm>${confirmLabel}</button>`;
    open(id);

    modal(id).querySelector("[data-dialog-confirm]").onclick = (event) =>
        submitting(event.currentTarget, async () => {
            await onConfirm();
            await close(id);
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
