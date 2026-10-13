import { mountDragRail } from "./drag-rail.js";

mountDragRail(document.getElementById("timeline"), {
    prev: document.querySelector("[data-timeline-prev]"),
    next: document.querySelector("[data-timeline-next]"),
    item: ".timeline-entry",
});
