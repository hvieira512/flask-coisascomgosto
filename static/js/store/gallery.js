import { ProductPlaceholder } from "./placeholder.js";
import { escapeHtml } from "../core/html.js";
import { StoreLightbox } from "./lightbox.js";

/**
 * Product gallery: a previewer with a strip of thumbnails under it.
 *
 * The previewer shows one image at a time. Arrows overlaid on it step to the
 * previous/next image and are revealed on hover; the strip scrolls sideways and
 * keeps the active thumbnail in view. Swiping steps too, and a tap opens the
 * photographs full screen through lightbox.js.
 *
 * Images arrive in groups — the chosen colour's photographs, then the piece's own —
 * and the strip labels them when there is more than one. Stepping and the fullscreen
 * view treat the set as one sequence.
 *
 * Only the chosen colour's photographs are ever here. Another colour's appear by
 * choosing that colour.
 */
export const StoreGallery = (function () {
    const GROUP_LABELS = { colour: "Esta cor", piece: "Da peça" };

    function create(root, product) {
        const galleryEl = root.querySelector(".gallery");
        const stage = root.querySelector("#gallery-stage");
        const stageImage = root.querySelector("#stage-image");
        const counter = root.querySelector("#stage-counter");
        const note = root.querySelector("#stage-note");
        const strip = root.querySelector("#thumb-strip");
        const emptyNotice = root.querySelector("#gallery-empty");
        const prevButton = root.querySelector("[data-prev]");
        const nextButton = root.querySelector("[data-next]");

        let images = [];
        let index = 0;
        /** Only whether a colour is chosen, which is what makes a piece photograph
         *  worth labelling: with no colours there is nothing to mistake it for. */
        let hasColourChosen = false;

        function show(next) {
            if (images.length === 0) return;

            // Wrap around so the arrows never dead-end.
            index = (next + images.length) % images.length;
            const image = images[index];

            stageImage.src = image.url;
            stageImage.alt = image.alt || "";
            counter.textContent = `${index + 1} / ${images.length}`;

            // The piece's own photograph would otherwise look like the chosen colour's,
            // most of all when that colour has none and these are all there is.
            const isPiece = hasColourChosen && image.group === "piece";
            note.hidden = !isPiece;
            note.textContent = isPiece ? "Fotografia da peça" : "";

            strip.querySelectorAll(".strip-thumb").forEach((thumb, position) => {
                const isActive = position === index;
                thumb.classList.toggle("is-active", isActive);
                if (isActive) {
                    thumb.scrollIntoView({ inline: "nearest", block: "nearest", behavior: "smooth" });
                }
            });
        }

        /**
         * The thumbnails, in one row, in labelled groups: the chosen colour's, then
         * the piece's own, then the other colours'. A single group carries no label —
         * there is nothing to tell apart.
         *
         * Presentation only. Each thumbnail keeps its place in the stable sequence the
         * arrows walk, so grouping them here reorders what is seen without reordering
         * what "next" means.
         */
        function renderStrip(all) {
            const numbered = all.map((image, position) => ({ image, position }));
            const groups = ["colour", "piece", "other"]
                .map((name) => ({
                    name,
                    items: numbered.filter(({ image }) => (image.group ?? "colour") === name),
                }))
                .filter(({ items }) => items.length);

            const labelled = groups.length > 1;

            return groups
                .map(({ name, items }) => `
                    <div class="strip-group">
                      ${labelled
                          ? `<p class="strip-label">${escapeHtml(GROUP_LABELS[name] ?? "")}</p>`
                          : ""}
                      <ul class="strip-track">
                        ${items.map(({ image, position }) => `
                          <li>
                            <button class="strip-thumb" type="button" data-index="${position}"
                                    aria-label="Ver imagem ${position + 1}">
                              <img src="${escapeHtml(image.url)}"
                                   alt="${escapeHtml(image.alt || "")}" loading="lazy">
                            </button>
                          </li>`).join("")}
                      </ul>
                    </div>`)
                .join("");
        }

        /** `variant` names which colour the empty state should be drawn in, and which
         *  photographs count as its own. */
        function render(nextImages, variant = null) {
            images = nextImages || [];
            hasColourChosen = Boolean(variant);
            index = 0;

            const hasImages = images.length > 0;
            stage.hidden = false;
            emptyNotice.hidden = true;

            // With no photographs the stage shows the product's placeholder.
            // The image and controls are hidden rather than replaced, so
            // switching to a variant that DOES have photos still works.
            const existing = stage.querySelector(".product-placeholder");
            if (existing) existing.remove();

            stageImage.hidden = !hasImages;

            if (!hasImages) {
                prevButton.disabled = true;
                nextButton.disabled = true;
                counter.hidden = true;
                note.hidden = true;
                strip.hidden = true;
                strip.innerHTML = "";

                if (product) {
                    stage.insertAdjacentHTML(
                        "afterbegin",
                        ProductPlaceholder.markup(
                            product, "product-placeholder--stage", variant?.color_set
                        )
                    );
                }
                return;
            }

            // A single image needs no navigation, and nothing to preview.
            const navigable = images.length > 1;
            prevButton.disabled = !navigable;
            nextButton.disabled = !navigable;
            counter.hidden = !navigable;
            strip.hidden = !navigable;

            strip.innerHTML = navigable ? renderStrip(images) : "";

            show(0);
        }

        prevButton.addEventListener("click", () => show(index - 1));
        nextButton.addEventListener("click", () => show(index + 1));

        strip.addEventListener("click", (event) => {
            const thumb = event.target.closest(".strip-thumb");
            if (thumb) show(Number(thumb.dataset.index));
        });

        // Arrow keys drive the previewer once it has focus.
        stage.addEventListener("keydown", (event) => {
            if (event.key === "ArrowLeft") show(index - 1);
            if (event.key === "ArrowRight") show(index + 1);
            if (event.key === "Enter" || event.key === " ") openLightbox();
        });
        stage.tabIndex = 0;

        // ----------------------------------------------------------------
        // Swipe, and the fullscreen view
        // ----------------------------------------------------------------

        const openLightbox = () => StoreLightbox.open(images, index);

        /** Past this many pixels the gesture is a swipe, not a tap. */
        const SWIPE_THRESHOLD = 40;
        let startX = null;
        let startY = null;

        stage.addEventListener("pointerdown", (event) => {
            startX = event.clientX;
            startY = event.clientY;
        });

        stage.addEventListener("pointerup", (event) => {
            if (startX === null) return;

            const dx = event.clientX - startX;
            const dy = event.clientY - startY;
            startX = null;

            // Ignore a mostly-vertical drag: that is the page scrolling.
            if (Math.abs(dx) > SWIPE_THRESHOLD && Math.abs(dx) > Math.abs(dy)) {
                show(index + (dx < 0 ? 1 : -1));
                return;
            }

            // A tap on the photograph opens it full screen. The arrows sit on
            // top of the stage, so a tap on one must not also open it.
            if (Math.abs(dx) < 8 && Math.abs(dy) < 8 &&
                !event.target.closest("[data-prev], [data-next]")) {
                openLightbox();
            }
        });

        stage.addEventListener("pointercancel", () => {
            startX = null;
        });

        return { render };
    }

    return { create };
})();
