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
        <button class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
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
            await close(id);
            if (success) Notify.success(success);
            await after?.(result);
        });
    };

    open(id);
    afterRender?.(root);
    show(0, { focus: false });
}
