import { Notify } from "./notify.js";
import { escapeHtml } from "./html.js";

export const PhotoPicker = (function () {
    const ACCEPT = "image/jpeg,image/png,image/webp";
    const MAX_BYTES = 5 * 1024 * 1024;

    const DEFAULT_HINT = "Arraste para aqui, escolha um ficheiro ou tire uma fotografia";

    function acceptable(file) {
        if (!file.type.startsWith("image/")) {
            Notify.error(`"${file.name}" não é uma imagem.`);
            return false;
        }
        if (file.size > MAX_BYTES) {
            Notify.error(`"${file.name}" passa dos ${MAX_BYTES / 1024 / 1024} MB.`);
            return false;
        }
        return true;
    }

    function mount(container, {
        multiple = false, hint = DEFAULT_HINT, initial = [], onRemoveStored = null,
        onAdd = null,
    } = {}) {
        const items = initial.map((item) => ({ ...item }));

        container.classList.add("photo-tray", "row", "g-2");
        container.classList.add(...(multiple
            ? ["row-cols-3", "row-cols-md-5"]
            : ["row-cols-1"]));

        function preview(item) {
            if (item.url) return item.url;
            if (!item.preview) item.preview = URL.createObjectURL(item.file);
            return item.preview;
        }

        function forget(item) {
            if (item.preview) URL.revokeObjectURL(item.preview);
        }

        function draw() {
            const slots = items.map((item, index) => `
                <div class="col">
                  <button type="button" class="photo-slot is-filled" data-photo-remove="${index}"
                          title="Remover" aria-label="Remover esta fotografia">
                    <img src="${escapeHtml(preview(item))}" alt="">
                    <span class="photo-slot-x disc" aria-hidden="true">
                      <i class="fa-solid fa-xmark"></i>
                    </span>
                  </button>
                </div>`);

            if (multiple || items.length === 0) {
                slots.push(`
                  <div class="col">
                    <label class="photo-slot" data-photo-empty>
                      <input type="file" accept="${ACCEPT}" capture="environment"
                             ${multiple ? "multiple" : ""} aria-label="Escolher fotografia">
                      <span class="photo-slot-prompt">
                        <span class="photo-slot-icon"><i class="fa-solid fa-camera"></i></span>
                        <span class="photo-slot-hint">${escapeHtml(hint)}</span>
                      </span>
                    </label>
                  </div>`);
            }

            container.innerHTML = slots.join("");
        }

        async function accept(files, at = null) {
            const chosen = [...files].filter(acceptable);
            if (!chosen.length) return;

            if (onAdd) {
                container.classList.add("is-busy");
                try {
                    await onAdd(chosen);
                } catch (error) {
                    Notify.error(error.message);
                } finally {
                    container.classList.remove("is-busy");
                }
                return;
            }

            if (at !== null) {
                forget(items[at]);
                items[at] = { file: chosen[0] };
            } else if (multiple) {
                items.push(...chosen.map((file) => ({ file })));
            } else {
                items.forEach(forget);
                items.length = 0;
                items.push({ file: chosen[0] });
            }
            draw();
        }

        async function remove(index) {
            const item = items[index];
            if (item.id && onRemoveStored) {
                try {
                    await onRemoveStored(item);
                } catch (error) {
                    if (error.message) Notify.error(error.message);
                    return;
                }
            }
            forget(item);
            items.splice(index, 1);
            draw();
        }

        container.addEventListener("change", (event) => {
            const input = event.target.closest('input[type="file"]');
            if (input?.files?.length) accept(input.files);
        });

        container.addEventListener("click", (event) => {
            const filled = event.target.closest("[data-photo-remove]");
            if (filled) remove(Number(filled.dataset.photoRemove));
        });

        container.addEventListener("dragover", (event) => {
            const slot = event.target.closest(".photo-slot");
            if (!slot) return;
            event.preventDefault();
            slot.classList.add("is-over");
        });

        container.addEventListener("dragleave", (event) => {
            event.target.closest(".photo-slot")?.classList.remove("is-over");
        });

        container.addEventListener("drop", (event) => {
            const slot = event.target.closest(".photo-slot");
            if (!slot) return;

            event.preventDefault();
            slot.classList.remove("is-over");
            const at = slot.dataset.photoRemove;
            accept(event.dataTransfer.files, at === undefined ? null : Number(at));
        });

        draw();

        return {
            files: () => items.filter((item) => item.file).map((item) => item.file),
            items: () => items.map((item) => ({ ...item })),
        };
    }

    return { mount, MAX_BYTES };
})();
