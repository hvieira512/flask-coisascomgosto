// Drag-to-scroll and arrow buttons for the horizontal events rail.
// Touch is left alone: it already pans natively.
(function () {
    const rail = document.getElementById("timeline");
    if (!rail) return;

    const prev = document.querySelector("[data-timeline-prev]");
    const next = document.querySelector("[data-timeline-next]");

    /** Past this many pixels a gesture is a drag, not a click. */
    const DRAG_THRESHOLD = 5;
    /** Tolerance for "we are at the end", since scrollLeft can be fractional. */
    const EDGE_SLACK = 2;

    /** One entry's width, so a click advances exactly one card. */
    function step() {
        const entry = rail.querySelector(".timeline-entry");
        return entry ? entry.getBoundingClientRect().width : rail.clientWidth;
    }

    function syncArrows() {
        if (!prev || !next) return;

        const maxScroll = rail.scrollWidth - rail.clientWidth;
        // Mobile stacks the rail; nothing to page through.
        const scrollable = maxScroll > EDGE_SLACK && getComputedStyle(rail).overflowX !== "visible";

        const atStart = rail.scrollLeft <= EDGE_SLACK;
        const atEnd = rail.scrollLeft >= maxScroll - EDGE_SLACK;

        prev.hidden = !scrollable || atStart;
        next.hidden = !scrollable || atEnd;

        // Fade an edge only while content sits past it, so an arrow never
        // covers solid text.
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
        rail.classList.add("is-dragging");
    });

    rail.addEventListener("pointermove", (event) => {
        if (!dragging) return;

        const delta = event.clientX - startX;
        moved = Math.max(moved, Math.abs(delta));
        rail.scrollLeft = startScroll - delta;

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
