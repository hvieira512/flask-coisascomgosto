/**
 * Drag-to-scroll and arrow buttons for a horizontal rail.
 *
 * Two rails use this: the fairs on the landing page and the collections above
 * the catalogue. It was written for the first and copied for nothing — the
 * second asked the same question, so it is the same code.
 *
 * Touch is left alone: it already pans natively.
 */

/** Past this many pixels a gesture is a drag, not a click. */
const DRAG_THRESHOLD = 5;
/** Tolerance for "we are at the end", since scrollLeft can be fractional. */
const EDGE_SLACK = 2;

/**
 * @param {HTMLElement} rail        the scroll container
 * @param {object}      controls    { prev, next, item } — item is the selector
 *                                  for one entry, so a click advances by one
 */
export function mountDragRail(rail, { prev, next, item }) {
    if (!rail) return;

    function step() {
        const entry = item ? rail.querySelector(item) : rail.firstElementChild;
        return entry ? entry.getBoundingClientRect().width : rail.clientWidth;
    }

    function syncArrows() {
        const maxScroll = rail.scrollWidth - rail.clientWidth;
        // A stacked rail — the phone layout — has nothing to page through.
        const scrollable =
            maxScroll > EDGE_SLACK && getComputedStyle(rail).overflowX !== "visible";
        const atStart = rail.scrollLeft <= EDGE_SLACK;
        const atEnd = rail.scrollLeft >= maxScroll - EDGE_SLACK;

        if (prev) prev.hidden = !scrollable || atStart;
        if (next) next.hidden = !scrollable || atEnd;

        // Fade an edge only while content sits past it, so an arrow never covers
        // solid text.
        rail.classList.toggle("has-fade-start", scrollable && !atStart);
        rail.classList.toggle("has-fade-end", scrollable && !atEnd);
    }

    prev?.addEventListener("click", () =>
        rail.scrollBy({ left: -step(), behavior: "smooth" })
    );
    next?.addEventListener("click", () =>
        rail.scrollBy({ left: step(), behavior: "smooth" })
    );

    rail.addEventListener("scroll", syncArrows, { passive: true });
    window.addEventListener("resize", syncArrows);
    syncArrows();

    let dragging = false;
    let moved = 0;
    let startX = 0;
    let startScroll = 0;

    rail.addEventListener("pointerdown", (event) => {
        if (event.pointerType === "touch") return;

        dragging = true;
        moved = 0;
        startX = event.clientX;
        startScroll = rail.scrollLeft;
    });

    rail.addEventListener("pointermove", (event) => {
        if (!dragging) return;

        const delta = event.clientX - startX;
        moved = Math.max(moved, Math.abs(delta));
        rail.scrollLeft = startScroll - delta;

        // Both of these wait for the gesture to actually be a drag. On
        // pointerdown they are wrong in ways that only show up on a rail whose
        // entries are controls: preventDefault on every move between down and up
        // cancels the click that follows, and the grabbing cursor is a lie until
        // something has moved.
        if (moved > DRAG_THRESHOLD) {
            rail.classList.add("is-dragging");
            event.preventDefault();
        }
    });

    function endDrag() {
        if (!dragging) return;
        dragging = false;
        rail.classList.remove("is-dragging");
        syncArrows();
    }

    rail.addEventListener("pointerup", endDrag);
    rail.addEventListener("pointercancel", endDrag);
    rail.addEventListener("pointerleave", endDrag);

    // A drag that ends on top of a link or a button must not activate it.
    rail.addEventListener(
        "click",
        (event) => {
            if (moved > DRAG_THRESHOLD) {
                event.preventDefault();
                event.stopPropagation();
            }
            moved = 0;
        },
        true
    );

    return { syncArrows };
}
