const DRAG_THRESHOLD = 5;
const EDGE_SLACK = 2;

export function mountDragRail(rail, { prev, next, item }) {
    if (!rail) return;

    function step() {
        const entry = item ? rail.querySelector(item) : rail.firstElementChild;
        return entry ? entry.getBoundingClientRect().width : rail.clientWidth;
    }

    function syncArrows() {
        const maxScroll = rail.scrollWidth - rail.clientWidth;
        const scrollable =
            maxScroll > EDGE_SLACK && getComputedStyle(rail).overflowX !== "visible";
        const atStart = rail.scrollLeft <= EDGE_SLACK;
        const atEnd = rail.scrollLeft >= maxScroll - EDGE_SLACK;

        if (prev) prev.hidden = !scrollable || atStart;
        if (next) next.hidden = !scrollable || atEnd;

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

        // Only once it is a drag: preventDefault on every move between down and
        // up cancels the click that follows, so a tile in the rail did nothing.
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
