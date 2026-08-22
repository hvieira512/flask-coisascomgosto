const MAX_PAGE_BUTTONS = 7;

function pageWindow(page, totalPages) {
    if (totalPages <= MAX_PAGE_BUTTONS) {
        return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    const around = [page - 1, page, page + 1].filter((n) => n > 1 && n < totalPages);
    const numbers = [1, ...around, totalPages];

    return numbers.flatMap((n, i) => (i > 0 && n - numbers[i - 1] > 1 ? [null, n] : [n]));
}

const arrow = (icon, label, target, disabled) => `
  <li class="page-item${disabled ? " disabled" : ""}">
    <button class="page-link" type="button" data-page="${target}"
            aria-label="${label}"${disabled ? " disabled" : ""}>
      <span class="icon is-small"><i class="fa-solid ${icon}"></i></span>
    </button>
  </li>`;

export function mountPagination(onGo) {
    const root = document.getElementById("pagination");
    const pageList = document.getElementById("page-list");
    let current = 1;
    let pages = 1;

    pageList.addEventListener("click", (event) => {
        const button = event.target.closest("[data-page]");
        if (!button || button.disabled) return;

        const wanted = Number(button.dataset.page);
        if (wanted === current || wanted < 1 || wanted > pages) return;

        onGo(wanted);
    });

    return {
        render(page, totalPages) {
            current = page;
            pages = totalPages;

            root.hidden = totalPages <= 1;
            if (root.hidden) {
                pageList.innerHTML = "";
                return;
            }

            const numbers = pageWindow(page, totalPages)
                .map((number) =>
                    number === null
                        ? `<li class="page-item disabled"><span class="page-link">&hellip;</span></li>`
                        : `<li class="page-item${number === page ? " active" : ""}">
                             <button class="page-link" type="button" data-page="${number}"
                                     aria-label="Página ${number}"
                                     ${number === page ? 'aria-current="page"' : ""}>
                               ${number}
                             </button>
                           </li>`
                )
                .join("");

            pageList.innerHTML =
                arrow("fa-chevron-left", "Página anterior", page - 1, page <= 1) +
                numbers +
                arrow("fa-chevron-right", "Página seguinte", page + 1, page >= totalPages);
        },
    };
}
