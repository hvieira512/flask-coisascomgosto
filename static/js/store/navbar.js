// Bulma ships the burger markup but no JavaScript.
//
// No DOMContentLoaded wrapper: this is a module, so it runs after the document is
// parsed — the event has already fired by then and the listener would never have
// run at all.
document.querySelectorAll("[data-navbar-burger]").forEach((burger) => {
    burger.addEventListener("click", () => {
        const menu = document.getElementById(burger.dataset.target);
        if (!menu) return;

        const isOpen = burger.classList.toggle("is-active");
        menu.classList.toggle("is-active", isOpen);
        burger.setAttribute("aria-expanded", String(isOpen));
    });
});
