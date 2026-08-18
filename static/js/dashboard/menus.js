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

    // Any click outside, or Escape, dismisses whatever is open. Escape inside a
    // dialog is the browser's own business — it fires `cancel` there.
    document.addEventListener("click", () => closeDropdowns(null));
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeDropdowns(null);
    });

    // ----------------------------------------------------------------
    // Modals — native <dialog>
    // ----------------------------------------------------------------

    // Closing only. Opening belongs to core/modal.js, because every dialog on
    // these pages needs its body built before it is any use — there was also a
    // data-modal-target opener here, which no template ever used.
    //
    // Delegated so buttons rendered later (table rows) work without rebinding.
    document.addEventListener("click", (event) => {
        if (event.target.closest("[data-modal-close]")) {
            event.preventDefault();
            event.target.closest("dialog")?.close();
            return;
        }

        // A click on the backdrop reports the dialog itself as its target, since
        // ::backdrop is not an element and the card covers the whole dialog box.
        //
        // Deliberately an identity check rather than "anything that is not inside
        // .modal-card": a confirmation raised from inside a dialog renders as a
        // sibling of the card, so the loose test read Cancelar as a backdrop click
        // and closed the form behind the question.
        if (event.target.matches("dialog.dash-dialog")) event.target.close();
    });
})();
