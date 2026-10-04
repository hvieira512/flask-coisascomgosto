import { API, request } from "../core/api.js";
import { Notify } from "../core/notify.js";
import { escapeHtml } from "../core/html.js";

const WINDOWS = [7, 30, 90];
const DEFAULT_DAYS = 7;

function chosenDays() {
    const asked = Number(new URLSearchParams(window.location.search).get("dias"));
    return WINDOWS.includes(asked) ? asked : DEFAULT_DAYS;
}

const period = (days) =>
    days === 7 ? "esta semana" : days === 30 ? "neste mês" : `nestes ${days} dias`;

function sparkline(series) {
    if (!series || series.length < 2) return "";

    const peak = Math.max(...series);
    if (peak === 0) return "";

    const step = 100 / (series.length - 1);
    const points = series
        .map((value, index) => `${(index * step).toFixed(1)},${(19 - (value / peak) * 18).toFixed(1)}`)
        .join(" ");

    return `
      <svg class="mt-auto pt-2" viewBox="0 0 100 20" preserveAspectRatio="none"
           width="100%" height="20" aria-hidden="true" focusable="false">
        <polyline points="${points}" fill="none" stroke="currentColor"
                  stroke-width="1" stroke-linejoin="round" vector-effect="non-scaling-stroke"
                  opacity=".45" />
      </svg>`;
}

function figure(key, label, value, previous, { hasHistory, series }) {
    const delta = value - previous;
    const show = hasHistory && previous > 0 && delta !== 0;
    const tone = delta > 0 ? "--ccg-ready" : "--ccg-attention";

    return `
      <div class="col d-flex flex-column p-3 border-end border-bottom dash-figure"
           data-figure="${key}">
        <b class="data fs-3 fw-medium lh-1">${value}</b>
        <span class="eyebrow mt-1 mb-0">${escapeHtml(label)}</span>
        ${show
            ? `<span class="fs-7 data" style="color: var(${tone})">
                 ${delta > 0 ? "▲" : "▼"} ${Math.abs(delta)} vs. período anterior
               </span>`
            : `<span class="fs-7 text-body-tertiary">&nbsp;</span>`}
        ${sparkline(series)}
      </div>`;
}

const FIGURES = [
    ["visits", "Visitas"],
    ["views", "Aberturas de peças"],
    ["pieces", "Peças diferentes"],
    ["enquiries", "Pedidos de informação"],
    ["searches", "Procuras"],
];

function renderTotals({ totals, previous, daily, window: win }, days) {
    const hasHistory = Boolean(win.counting_since);
    const cards = FIGURES.map(([key, label]) =>
        figure(key, label, totals[key], previous[key], {
            hasHistory,
            series: daily[key],
        })
    ).join("");

    document.getElementById("totals").innerHTML = `
      <p class="eyebrow mb-2">O que aconteceu ${escapeHtml(period(days))}</p>
      <div class="row row-cols-2 row-cols-lg-5 g-0 border-top border-start">${cards}</div>
      ${hasHistory
          ? `<p class="help mt-2 mb-0">
               Uma visita é alguém a abrir a loja, contada uma vez por visita; uma
               abertura é a página de uma peça, também uma vez por visita. Um
               pedido é um clique em “Pedir informações”.
             </p>`
          : `<p class="help mt-2 mb-0">
               Ainda não há nada registado. A contagem começa quando alguém
               visitar a loja.
             </p>`}`;
}

function nothing(counting_since, quiet) {
    if (!counting_since) return `<p class="help mb-0">—</p>`;
    return `<p class="help mb-0">${escapeHtml(quiet)}</p>`;
}

function renderMostViewed({ top_products: pieces, window: win }) {
    const target = document.getElementById("most-viewed");

    if (!pieces.length) {
        target.innerHTML = nothing(win.counting_since, "Ninguém abriu uma peça neste período.");
        return;
    }

    target.innerHTML = `
      <ul class="list-group list-group-flush">
        ${pieces
            .map((piece) => `
              <li class="list-group-item d-flex justify-content-between align-items-center gap-2 px-0">
                <a href="/dashboard/products?q=${encodeURIComponent(piece.name)}">
                  ${escapeHtml(piece.name)}
                </a>
                <span class="d-flex align-items-center gap-2">
                  <span class="data text-body-secondary">${piece.views}</span>
                  ${piece.enquiries
                      ? `<span class="badge rounded-pill chip is-ready">${piece.enquiries} ${piece.enquiries === 1 ? "pedido" : "pedidos"}</span>`
                      : `<span class="fs-7 text-body-tertiary">sem pedidos</span>`}
                </span>
              </li>`)
            .join("")}
      </ul>`;
}

function renderAskedColors({ top_color_sets: sets, window: win }) {
    const target = document.getElementById("asked-colors");

    if (!sets.length) {
        target.innerHTML = nothing(
            win.counting_since,
            "Ninguém perguntou por uma cor neste período."
        );
        return;
    }

    target.innerHTML = `
      <ul class="list-group list-group-flush">
        ${sets
            .map((set) => `
              <li class="list-group-item d-flex justify-content-between align-items-center gap-2 px-0">
                <span>${escapeHtml(set.name)}</span>
                <span class="data text-body-secondary">${set.enquiries}</span>
              </li>`)
            .join("")}
      </ul>`;
}

function renderTopFilters({ top_filters: filters, window: win }) {
    const target = document.getElementById("top-filters");

    if (!filters.length) {
        target.innerHTML = nothing(win.counting_since, "Ninguém filtrou neste período.");
        return;
    }

    target.innerHTML = `
      <ul class="list-group list-group-flush">
        ${filters
            .map((filter) => `
              <li class="list-group-item d-flex justify-content-between align-items-center gap-2 px-0">
                <span>
                  <span class="text-body-secondary fs-7">${escapeHtml(filter.facet)}:</span>
                  ${escapeHtml(filter.label)}
                </span>
                <span class="data text-body-secondary">${filter.count}</span>
              </li>`)
            .join("")}
      </ul>`;
}

function renderCatalogue({ catalogue, window: win }) {
    // null when the window reaches back before pieces were dated at all, and 0
    // is nothing to announce.
    const added = catalogue.added
        ? ` (${catalogue.added} ${catalogue.added === 1 ? "nova" : "novas"})`
        : "";

    const parts = [
        `${catalogue.products} ${catalogue.products === 1 ? "peça" : "peças"}${added}`,
        `${catalogue.color_sets} ${catalogue.color_sets === 1 ? "conjunto de cor" : "conjuntos de cor"}`,
        `${catalogue.collections} ${catalogue.collections === 1 ? "colecção" : "colecções"}`,
        `${catalogue.colors} ${catalogue.colors === 1 ? "cor" : "cores"}`,
    ];

    if (win.counting_since) {
        const since = new Date(win.counting_since).toLocaleDateString("pt-PT");
        parts.push(`a contar desde ${since}`);
    }

    document.getElementById("catalogue-line").textContent = parts.join(" · ");
}

function markWindow(days) {
    document.querySelectorAll("[data-days]").forEach((button) => {
        const on = Number(button.dataset.days) === days;
        button.classList.toggle("btn-dark", on);
        button.classList.toggle("btn-outline-secondary", !on);
        button.setAttribute("aria-pressed", String(on));
    });
}

async function load(days) {
    markWindow(days);

    let overview;
    try {
        overview = await request(API.analytics.overview, { params: { days } });
    } catch (error) {
        Notify.error("Não foi possível carregar o painel.");
        console.error(error);
        return;
    }

    renderCatalogue(overview);
    renderTotals(overview, days);
    renderMostViewed(overview);
    renderAskedColors(overview);
    renderTopFilters(overview);
}

document.querySelector("[data-days]")?.parentElement?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-days]");
    if (!button) return;

    const days = Number(button.dataset.days);
    const url = new URL(window.location.href);
    url.searchParams.set("dias", String(days));
    window.history.replaceState({}, "", url);

    load(days);
});

load(chosenDays());
