/**
 * Notifications, on top of SweetAlert2.
 *
 *     Notify.success("Sessão iniciada.");
 *     await Notify.confirm("Apagar este produto?", { danger: true });
 */
const Notify = (function () {
    if (typeof Swal === "undefined") {
        console.error("SweetAlert2 is not loaded — notifications are disabled.");
    }

    const BRAND = "#4472C4";   // --ccg-blue-500
    const DANGER = "#C62828";

    /**
     * Where to render, which is not always <body>.
     *
     * A dialog opened with showModal() is promoted to the browser's top layer,
     * and the top layer paints above every z-index there is — so a toast appended
     * to <body> came out *behind* the dialog's own backdrop. Filling in a form and
     * being told nothing was wrong, while the reason sat invisible behind the
     * overlay, is the worst version of this.
     *
     * Rendering inside the open dialog puts the toast in the top layer with it.
     * The last open one wins: creating a product opens the edit dialog over the
     * wizard, and the message belongs to whichever is on top.
     */
    const host = () => {
        const dialogs = document.querySelectorAll("dialog[open]");
        return dialogs.length ? dialogs[dialogs.length - 1] : document.body;
    };

    const TOAST_DEFAULTS = {
        toast: true,
        position: "top-end",
        showConfirmButton: false,
        timer: 3200,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener("mouseenter", Swal.stopTimer);
            toast.addEventListener("mouseleave", Swal.resumeTimer);
        },
    };

    function toast(icon, title) {
        if (typeof Swal === "undefined") return Promise.resolve();
        return Swal.fire({ ...TOAST_DEFAULTS, icon, title, target: host() });
    }

    return {
        success: (message) => toast("success", message),
        error: (message) => toast("error", message),

        /** One short value, for a rename that does not deserve a modal form. */
        prompt: async (title, { value = "", confirmText = "Guardar" } = {}) => {
            if (typeof Swal === "undefined") return null;

            const result = await Swal.fire({
                target: host(),
                title,
                input: "text",
                inputValue: value,
                showCancelButton: true,
                confirmButtonText: confirmText,
                cancelButtonText: "Cancelar",
                confirmButtonColor: BRAND,
                cancelButtonColor: "#6B7280",
                reverseButtons: true,
                inputValidator: (entered) =>
                    entered.trim() ? undefined : "Escreva um nome.",
            });
            return result.isConfirmed ? result.value.trim() : null;
        },

        // False on cancel, Escape and backdrop dismissal alike.
        confirm: async (title, { text = "", confirmText = "Confirmar",
                                 danger = false } = {}) => {
            if (typeof Swal === "undefined") return false;

            const result = await Swal.fire({
                target: host(),
                title,
                text,
                icon: danger ? "warning" : "question",
                showCancelButton: true,
                confirmButtonText: confirmText,
                cancelButtonText: "Cancelar",
                confirmButtonColor: danger ? DANGER : BRAND,
                cancelButtonColor: "#6B7280",
                reverseButtons: true,
            });
            return result.isConfirmed === true;
        },
    };
})();

export { Notify };
