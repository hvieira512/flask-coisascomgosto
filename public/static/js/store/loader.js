(function () {
    const loader = document.getElementById("page-loader");
    if (!loader) return;

    // Long enough for the butterfly to finish drawing itself.
    const MIN_SHOWN = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 1400;

    function dismiss() {
        if (loader.classList.contains("is-done")) return;
        setTimeout(() => {
            loader.classList.add("is-done");
            setTimeout(() => loader.remove(), 400);
        }, Math.max(0, MIN_SHOWN - performance.now()));
    }

    if (document.readyState === "complete") {
        dismiss();
    } else {
        window.addEventListener("load", dismiss);
    }

    setTimeout(dismiss, 3000);
})();
