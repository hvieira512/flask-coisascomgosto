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
 * Only the chosen colour's photographs are ever here. Another colour's appear by
 * choosing that colour. They used to arrive in labelled groups, because a
 * photograph could belong to the piece rather than to a colour; every photograph
 * belongs to a colour now, so there is one group and nothing to label.
 */
export const StoreGallery = (function () {
    function create(root, product) {
        const galleryEl = root.querySelector(".gallery");
        const stage = root.querySelector("#gallery-stage");
        const stageImage = root.querySelector("#stage-image");
        const counter = root.querySelector("#stage-counter");
        const strip = root.querySelector("#thumb-strip");
        const emptyNotice = root.querySelector("#gallery-empty");
        const prevButton = root.querySelector("[data-prev]");
        const nextButton = root.querySelector("[data-next]");

        let images = [];
        let index = 0;

        function show(next) {
            if (images.length === 0) return;

            // Wrap around so the arrows never dead-end.
            index = (next + images.length) % images.length;
            const image = images[index];

            stageImage.src = image.url;
            stageImage.alt = image.alt || "";
            counter.textContent = `${index + 1} / ${images.length}`;

            strip.querySelectorAll(".strip-thumb").forEach((thumb, position) => {
                const isActive = position === index;
                thumb.classList.toggle("is-active", isActive);
                if (isActive) {
                    thumb.scrollIntoView({ inline: "nearest", block: "nearest", behavior: "smooth" });
                }
            });
        }

        /** The thumbnails, in one row, in the order the arrows walk. */
        function renderStrip(all) {
            return `
                <div class="strip-group">
                  <ul class="strip-track">
                    ${all.map((image, position) => `
                      <li>
                        <button class="strip-thumb" type="button" data-index="${position}"
                                aria-label="Ver imagem ${position + 1}">
                          <img src="${escapeHtml(image.url)}"
                               alt="${escapeHtml(image.alt || "")}" loading="lazy">
                        </button>
                      </li>`).join("")}
                  </ul>
                </div>`;
        }

        /** `variant` names which colour the empty state should be drawn in. */
        function render(nextImages, variant = null) {
            images = nextImages || [];
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
