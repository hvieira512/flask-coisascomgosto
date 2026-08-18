/**
 * Fullscreen, zoomable view of the product photographs, on PhotoSwipe.
 *
 * PhotoSwipe 5 ships ESM only, which is what first forced a module into a
 * codebase of classic scripts — and left this publishing a global for gallery.js
 * to find at click time, because a deferred module had not run when the gallery
 * was built. Now that everything is a module, gallery.js imports it.
 */

import PhotoSwipe from "../../photoswipe/photoswipe.esm.min.js";

/**
 * PhotoSwipe wants each slide's natural size to compute its zoom.
 * Our images carry no dimensions, so they are measured once, on open. They are
 * already in the browser cache — the stage has been showing one of them.
 */
async function measure(image) {
    return new Promise((resolve) => {
        const probe = new Image();
        probe.onload = () =>
            resolve({ width: probe.naturalWidth, height: probe.naturalHeight });
        // A broken image must not stop the lightbox opening.
        probe.onerror = () => resolve({ width: 1600, height: 1600 });
        probe.src = image.url;
    });
}

export const StoreLightbox = {
    async open(images, index = 0) {
        if (!images || images.length === 0) return;

        const sizes = await Promise.all(images.map(measure));

        new PhotoSwipe({
            dataSource: images.map((image, position) => ({
                src: image.url,
                alt: image.alt || "",
                width: sizes[position].width,
                height: sizes[position].height,
            })),
            index,
            // Opaque: a product photograph is easier to judge without the page
            // bleeding through behind it.
            bgOpacity: 1,
            closeTitle: "Fechar",
            zoomTitle: "Ampliar",
            arrowPrevTitle: "Anterior",
            arrowNextTitle: "Seguinte",
            errorMsg: "Não foi possível carregar a fotografia.",
        }).init();
    },
};
