/**
 * A dialog that asks for one group of fields at a time.
 *
 * For creating something big enough that a single screen puts questions in front
 * of the owners before they can answer them. The required fields come first and
 * nothing is written until the last step, so the record never exists half-made.
 *
 * The caller owns the markup and marks each group with `data-step`; this only
 * supplies the chrome — where you are, Voltar/Continuar, and which group shows.
 * Every group stays in the DOM the whole time, so going back and forth keeps what
 * has been typed.
 */

import { bodyOf, close, footOf, modal, open, submitting } from "./modal.js";
import { Notify } from "./notify.js";

export function stepDialog({
    id, body, titles, validate = [], finishLabel, onFinish, success, after, afterRender,
}) {
    bodyOf(id).innerHTML = `
        <div class="mb-4">
          <p class="eyebrow mb-2" data-step-label></p>
          <div class="progress step-progress" data-step-progress role="progressbar"
               aria-label="Progresso" aria-valuemin="1" aria-valuemax="${titles.length}">
            <div class="progress-bar" data-step-progress-bar></div>
          </div>
        </div>
        ${body}`;

    footOf(id).innerHTML = `
        <button class="btn btn-outline-secondary" data-modal-close>Cancelar</button>
        <button class="btn btn-outline-secondary" data-step-back>Voltar</button>
        <button class="btn btn-dark" data-step-next></button>`;

    const root = modal(id);
    const panels = [...root.querySelectorAll("[data-step]")];
    const label = root.querySelector("[data-step-label]");
    const progress = root.querySelector("[data-step-progress]");
    const progressBar = root.querySelector("[data-step-progress-bar]");
    const back = root.querySelector("[data-step-back]");
    const next = root.querySelector("[data-step-next]");

    let current = 0;
    const last = () => current === panels.length - 1;

    function show(index, { focus = true, from = "right" } = {}) {
        current = index;
        // Which way the group travels in. Un-hiding restarts the CSS animation,
        // so the slide needs nothing here but the direction.
        panels[index].style.setProperty("--step-from", from === "left" ? "-1.5rem" : "1.5rem");
        panels.forEach((panel, i) => { panel.hidden = i !== index; });

        label.textContent = `Passo ${index + 1} de ${panels.length} · ${titles[index]}`;
        progress.setAttribute("aria-valuenow", String(index + 1));
        progressBar.style.width = `${((index + 1) / panels.length) * 100}%`;
        back.hidden = index === 0;
        next.textContent = last() ? finishLabel : "Continuar";

        if (focus) {
            panels[index].querySelector(":is(input, textarea, select)")?.focus();
        }
    }

    back.onclick = () => show(current - 1, { from: "left" });

    next.onclick = (event) => {
        // A step's own check runs before leaving it, so a missing name is caught
        // on the step that asks for it rather than three screens later.
        if (!last()) {
            try {
                validate[current]?.(root);
            } catch (error) {
                Notify.error(error.message);
                return;
            }
            show(current + 1);
            return;
        }

        return submitting(event.currentTarget, async () => {
            validate[current]?.(root);
            const result = await onFinish(root);
            close(id);
            if (success) Notify.success(success);
            await after?.(result);
        });
    };

    // open() focuses the first field in the body, which is on step 1 anyway.
    open(id);
    afterRender?.(root);
    show(0, { focus: false });
}
