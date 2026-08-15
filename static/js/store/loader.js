/**
 * Dismisses the breathing-butterfly loader.
 *
 * Fades out as soon as the page is ready, with no artificial minimum — on a
 * fast load that is a brief graceful pass, which is the intent. The element is
 * removed from the DOM after the fade so it can never trap focus or clicks.
 */
(function () {
    const loader = document.getElementById("page-loader");
    if (!loader) return;

    function dismiss() {
        if (loader.classList.contains("is-done")) return;
        loader.classList.add("is-done");

        // Match the .45s CSS transition, then take it out of the document.
        setTimeout(() => loader.remove(), 500);
    }

    if (document.readyState === "complete") {
        dismiss();
    } else {
        window.addEventListener("load", dismiss);
    }

    // Belt and braces: if `load` never fires (a stalled image, a slow font),
    // do not hold the page hostage.
    setTimeout(dismiss, 3000);
})();
