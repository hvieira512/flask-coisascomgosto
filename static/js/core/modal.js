import { Notify } from "./notify.js";

export const modal = (id) => document.getElementById(id);
export const bodyOf = (id) => modal(id).querySelector(".modal-body");
export const footOf = (id) => modal(id).querySelector(".modal-footer");

const instance = (id) => bootstrap.Modal.getOrCreateInstance(modal(id));

const opened = new WeakMap();

export const open = (id) => {
    const element = modal(id);
    if (!element) return;

    opened.set(element, new Promise((resolve) => {
        element.addEventListener("shown.bs.modal", resolve, { once: true });
    }));

    element.addEventListener("shown.bs.modal", () => {
        element.querySelector(".modal-body :is(input, textarea, select)")?.focus();
    }, { once: true });

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

    await opened.get(element);
    instance(id).hide();
};

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
