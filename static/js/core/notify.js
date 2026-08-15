/**
 * Notifications, on top of SweetAlert2.
 *
 * SweetAlert2 needs a block of configuration for every toast — position, timer,
 * progress bar, no backdrop. Repeating that at each call site would be noise and
 * would drift, so it lives here once and callers keep writing one-liners:
 *
 *     Notify.success("Sessão iniciada.");
 *     Notify.error("Não foi possível guardar.");
 *     await Notify.confirm("Apagar este produto?");
 *
 * `confirm` replaces the browser's window.confirm, which cannot be styled and
 * blocks the page. It resolves to true only when the user accepts.
 *
 * Labels are Portuguese because they are user-facing; everything else is
 * English, like the rest of the codebase.
 */
window.Notify = (function () {
    if (typeof Swal === "undefined") {
        // Better a clear console error than "Notify is not defined" thrown from
        // whichever page happened to be first to report something.
        console.error("SweetAlert2 is not loaded — notifications are disabled.");
    }

    /** Brand blue, matching --ccg-blue-500 in static/css/theme.css. */
    const BRAND = "#4472C4";
    const DANGER = "#C62828";

    const TOAST_DEFAULTS = {
        toast: true,
        position: "top-end",
        showConfirmButton: false,
        timer: 3200,
        timerProgressBar: true,
        // Pausing on hover means a message is never missed while reading it.
        didOpen: (toast) => {
            toast.addEventListener("mouseenter", Swal.stopTimer);
            toast.addEventListener("mouseleave", Swal.resumeTimer);
        },
    };

    function toast(icon, title) {
        if (typeof Swal === "undefined") return Promise.resolve();
        return Swal.fire({ ...TOAST_DEFAULTS, icon, title });
    }

    return {
        success: (message) => toast("success", message),
        error: (message) => toast("error", message),
        warning: (message) => toast("warning", message),
        info: (message) => toast("info", message),

        /**
         * A modal yes/no. Resolves true when confirmed, false otherwise —
         * including when the user dismisses with Escape or the backdrop.
         */
        confirm: async (title, { text = "", confirmText = "Confirmar",
                                 danger = false } = {}) => {
            if (typeof Swal === "undefined") return false;

            const result = await Swal.fire({
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
