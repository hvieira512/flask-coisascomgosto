(function () {
    const loader = document.getElementById("page-loader");
    if (!loader) return;

    function dismiss() {
        if (loader.classList.contains("is-done")) return;
        loader.classList.add("is-done");
        setTimeout(() => loader.remove(), 500);
    }

    if (document.readyState === "complete") {
        dismiss();
    } else {
        window.addEventListener("load", dismiss);
    }

    setTimeout(dismiss, 3000);
})();
