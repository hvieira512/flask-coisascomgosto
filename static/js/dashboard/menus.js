/**
 * Dashboard chrome: closing modals.
 *
 * The sidebar (Bootstrap offcanvas) and the user menu (Bootstrap dropdown) are
 * wired by Bootstrap's own data-api, so nothing here touches them. Modals are a
 * native <dialog> rather than Bootstrap's, and closing them is the one piece the
 * browser does not do for us.
 *
 * Opening belongs to core/modal.js, because every dialog on these pages needs
 * its body built before it is any use.
 *
 * Delegated so buttons rendered later (table rows) work without rebinding.
 */
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
    // .modal-content": a confirmation raised from inside a dialog renders as a
    // sibling of the card, so the loose test read Cancelar as a backdrop click
    // and closed the form behind the question.
    if (event.target.matches("dialog.dash-dialog")) event.target.close();
});
