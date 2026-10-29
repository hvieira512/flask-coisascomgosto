import { Track } from "./track.js";

// Once the page is in. Sent while the modules were still arriving, the beacon's
// round trip through the app closed the connection the browser had queued the
// next module on, and the catalogue came up dead on a slow machine.
if (document.readyState === "complete") {
    Track.visit();
} else {
    window.addEventListener("load", () => Track.visit(), { once: true });
}
