import PhotoSwipe from "../../photoswipe/photoswipe.esm.min.js";

async function measure(image) {
    return new Promise((resolve) => {
        const probe = new Image();
        probe.onload = () =>
            resolve({ width: probe.naturalWidth, height: probe.naturalHeight });
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
            bgOpacity: 1,
            closeTitle: "Fechar",
            zoomTitle: "Ampliar",
            arrowPrevTitle: "Anterior",
            arrowNextTitle: "Seguinte",
            errorMsg: "Não foi possível carregar a fotografia.",
        }).init();
    },
};
