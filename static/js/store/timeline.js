// The fairs rail. Its behaviour is shared with the collections rail above the
// catalogue — see drag-rail.js.
import { mountDragRail } from "./drag-rail.js";

mountDragRail(document.getElementById("timeline"), {
    prev: document.querySelector("[data-timeline-prev]"),
    next: document.querySelector("[data-timeline-next]"),
    item: ".timeline-entry",
});
