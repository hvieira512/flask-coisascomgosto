(function () {
    const loader = document.getElementById("page-loader");
    if (!loader) return;

    function dismiss() {
        if (loader.classList.contains("is-done")) return;
        loader.classList.add("is-done");
        setTimeout(() => loader.remove(), 500);   // matches the .45s CSS fade
    }

    if (document.readyState === "complete") {
        dismiss();
    } else {
        window.addEventListener("load", dismiss);
    }

    // If `load` never fires — a stalled image, a slow font — do not hold the
    // page hostage behind the loader.
    setTimeout(dismiss, 3000);
})();
