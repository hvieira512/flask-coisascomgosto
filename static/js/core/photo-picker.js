/**
 * A place to put photographs: an empty area to drop, choose or shoot into, and a
 * filled area showing what was put there.
 *
 *     const tray = PhotoPicker.mount(element, { multiple: true });
 *     tray.files();   // the File objects, in the order they were added
 *
 * A slot holds exactly one photograph and fills itself with it. `multiple` keeps an
 * empty slot after the filled ones, which is how a variant ends up with several.
 *
 * Nothing is uploaded here. The files are held until the caller has somewhere to
 * put them — a photograph needs a product id, and in the create wizard that does
 * not exist until the last button.
 */

import { Notify } from "./notify.js";
import { escapeHtml } from "./html.js";

export const PhotoPicker = (function () {
    const ACCEPT = "image/jpeg,image/png,image/webp";
    /** uploads.MAX_BYTES. The server checks too; refusing here saves the owner
     *  watching a five-megabyte upload finish and then be turned away. */
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

    /**
     * @param {Element} container where to draw
     * @param {object} options
     *   multiple        keep an empty slot after the filled ones
     *   hint            the helper text under the camera
     *   initial         photographs already saved: [{ id, url }]
     *   onRemoveStored  async, called before dropping a saved one; throw to keep it
     *   onAdd           async, called with the files just chosen. Given one, the
     *                   component hands them over instead of holding them: the caller
     *                   has somewhere to put them now and is expected to re-render
     *                   from whatever came back. Without one the files are held for
     *                   `files()`, which is what the create wizard needs.
     */
    function mount(container, {
        multiple = false, hint = DEFAULT_HINT, initial = [], onRemoveStored = null,
        onAdd = null,
    } = {}) {
        // { file, preview } for one that is only held; { id, url } for one already
        // saved. Held in here rather than in the inputs: the slots are redrawn on
        // every change, and redrawing an <input type="file"> empties it.
        const items = initial.map((item) => ({ ...item }));

        // One photograph and nowhere for a second gets a single column: it fills
        // what it is given, and the column it sits in does the constraining — the
        // collections form puts it beside the fields rather than under them.
        container.classList.add("photo-tray", "row", "g-2");
        container.classList.add(...(multiple
            ? ["row-cols-2", "row-cols-sm-3"]
            : ["row-cols-1"]));

        function preview(item) {
            if (item.url) return item.url;
            if (!item.preview) item.preview = URL.createObjectURL(item.file);
            return item.preview;
        }

        function forget(item) {
            // Or every re-pick leaves another blob behind for the tab's lifetime.
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

        /** `at` replaces that slot; otherwise the files are added to the end. */
        async function accept(files, at = null) {
            const chosen = [...files].filter(acceptable);
            if (!chosen.length) return;

            if (onAdd) {
                // Marked while the upload runs, so a slow one does not look ignored.
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
                    // A message means it went wrong; none means the caller simply said
                    // no — a cancelled confirmation is not an error to report.
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

        // The whole slot is a drop target, filled or empty, so a photograph can be
        // replaced by dropping over the one it replaces.
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
            /** The held photographs, for the caller to upload once it can. */
            files: () => items.filter((item) => item.file).map((item) => item.file),
            /** Everything, held and saved alike. */
            items: () => items.map((item) => ({ ...item })),
        };
    }

    return { mount, MAX_BYTES };
})();
