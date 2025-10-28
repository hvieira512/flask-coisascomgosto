export function renderLoading(el) {
    const container = typeof el === "string" ? document.querySelector(el) : el;

    if (!container) return;

    const loadingElement = document.createElement("div");
    loadingElement.classList.add("loading-overlay");

    loadingElement.innerHTML = `
        <div class="d-flex justify-content-center align-items-center h-100">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">A carregar...</span>
            </div>
        </div>
    `;

    Object.assign(loadingElement.style, {
        position: "absolute",
        top: "0",
        left: "0",
        width: "100%",
        height: "100%",
        backgroundColor: "rgba(255, 255, 255, 0.8)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        zIndex: "998",
    });

    container.style.position = "relative";
    container.appendChild(loadingElement);
}

export function removeLoading(el) {
    const container = typeof el === "string" ? document.querySelector(el) : el;
    const loadingElement = container?.querySelector(".loading-overlay");

    if (!container || !loadingElement) return;

    container.removeChild(loadingElement);
}
