/**
 * Dashboard chrome: sidebar overlay, navbar dropdowns and modals.
 *
 * Bulma ships the markup for all three but no JavaScript, so the behaviour
 * Bootstrap used to provide via data-bs-* attributes is wired here instead.
 */
(function () {
    // ----------------------------------------------------------------
    // Sidebar (overlay on small screens)
    // ----------------------------------------------------------------

    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const toggle = document.getElementById("sidebarToggle");

    function setSidebar(open) {
        sidebar.classList.toggle("is-open", open);
        overlay.classList.toggle("is-open", open);
    }

    if (toggle) {
        toggle.addEventListener("click", () => setSidebar(!sidebar.classList.contains("is-open")));
    }
    if (overlay) {
        overlay.addEventListener("click", () => setSidebar(false));
    }

    // ----------------------------------------------------------------
    // Navbar dropdowns
    // ----------------------------------------------------------------

    const dropdowns = [...document.querySelectorAll("[data-dropdown]")];

    function closeDropdowns(except) {
        dropdowns.forEach((dropdown) => {
            if (dropdown === except) return;
            dropdown.classList.remove("is-active");
            dropdown
                .querySelector("[data-dropdown-trigger]")
                ?.setAttribute("aria-expanded", "false");
        });
    }

    dropdowns.forEach((dropdown) => {
        const trigger = dropdown.querySelector("[data-dropdown-trigger]");
        if (!trigger) return;

        trigger.addEventListener("click", (event) => {
            event.stopPropagation();
            const isOpen = dropdown.classList.toggle("is-active");
            trigger.setAttribute("aria-expanded", String(isOpen));
            closeDropdowns(dropdown);
        });
    });

    // Any click outside, or Escape, dismisses whatever is open.
    document.addEventListener("click", () => closeDropdowns(null));
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeDropdowns(null);
            closeModals();
        }
    });

    // ----------------------------------------------------------------
    // Modals
    // ----------------------------------------------------------------

    function openModal(id) {
        document.getElementById(id)?.classList.add("is-active");
    }

    function closeModals() {
        document
            .querySelectorAll(".modal.is-active")
            .forEach((modal) => modal.classList.remove("is-active"));
    }

    // Delegated so buttons rendered later (product cards) work without rebinding.
    document.addEventListener("click", (event) => {
        const opener = event.target.closest("[data-modal-target]");
        if (opener) {
            event.preventDefault();
            openModal(opener.dataset.modalTarget);
            return;
        }

        if (event.target.closest("[data-modal-close]")) {
            event.preventDefault();
            closeModals();
        }
    });

    window.DashboardModals = { open: openModal, close: closeModals };
})();
