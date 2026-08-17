/**
 * Notifications, on top of SweetAlert2.
 *
 *     Notify.success("Sessão iniciada.");
 *     await Notify.confirm("Apagar este produto?", { danger: true });
 */
window.Notify = (function () {
    if (typeof Swal === "undefined") {
        console.error("SweetAlert2 is not loaded — notifications are disabled.");
    }

    const BRAND = "#4472C4";   // --ccg-blue-500
    const DANGER = "#C62828";

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
        return Swal.fire({ ...TOAST_DEFAULTS, icon, title });
    }

    return {
        success: (message) => toast("success", message),
        error: (message) => toast("error", message),

        // False on cancel, Escape and backdrop dismissal alike.
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
