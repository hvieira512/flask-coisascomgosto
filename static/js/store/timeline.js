/**
 * Horizontal events timeline: click-and-drag plus arrow buttons.
 *
 * The rail is a normal overflow-x container, so it already scrolls with a
 * trackpad, a touch swipe, or the keyboard when focused. This adds the two
 * affordances that need scripting:
 *
 *   - click-and-drag for mouse users
 *   - previous / next buttons for visitors who would rather not drag
 *
 * Only mouse input is intercepted for dragging: touch already pans natively,
 * and hijacking it would fight the browser's momentum scrolling.
 */
(function () {
    const rail = document.getElementById("timeline");
    if (!rail) return;

    const prev = document.querySelector("[data-timeline-prev]");
    const next = document.querySelector("[data-timeline-next]");

    /** Past this many pixels a gesture is a drag, not a click. */
    const DRAG_THRESHOLD = 5;
    /** Tolerance for "we are at the end", since scrollLeft can be fractional. */
    const EDGE_SLACK = 2;

    // ----------------------------------------------------------------
    // Arrow buttons
    // ----------------------------------------------------------------

    /** One entry's width, so a click advances exactly one card. */
    function step() {
        const entry = rail.querySelector(".timeline-entry");
        return entry ? entry.getBoundingClientRect().width : rail.clientWidth;
    }

    /** Hide the arrows entirely when they would do nothing. */
    function syncArrows() {
        if (!prev || !next) return;

        const maxScroll = rail.scrollWidth - rail.clientWidth;
        // Mobile stacks the rail vertically; there is nothing to page through.
        const scrollable = maxScroll > EDGE_SLACK && getComputedStyle(rail).overflowX !== "visible";

        const atStart = rail.scrollLeft <= EDGE_SLACK;
        const atEnd = rail.scrollLeft >= maxScroll - EDGE_SLACK;

        prev.hidden = !scrollable || atStart;
        next.hidden = !scrollable || atEnd;

        // An edge is faded only while it has content past it — which is exactly
        // when its arrow is showing, so the arrow never covers solid text.
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

    // ----------------------------------------------------------------
    // Click and drag
    // ----------------------------------------------------------------

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
        rail.classList.add("is-dragging");
    });

    rail.addEventListener("pointermove", (event) => {
        if (!dragging) return;

        const delta = event.clientX - startX;
        moved = Math.max(moved, Math.abs(delta));
        rail.scrollLeft = startScroll - delta;

        // Stops the browser selecting text across entries mid-drag.
        event.preventDefault();
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

    // A drag that ends on top of an event link must not follow it.
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
})();
