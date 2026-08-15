// Bulma ships the burger markup but no JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-navbar-burger]").forEach((burger) => {
        burger.addEventListener("click", () => {
            const menu = document.getElementById(burger.dataset.target);
            if (!menu) return;

            const isOpen = burger.classList.toggle("is-active");
            menu.classList.toggle("is-active", isOpen);
            burger.setAttribute("aria-expanded", String(isOpen));
        });
    });
});
