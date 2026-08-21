import { API, request } from "../core/api.js";
import { Notify } from "../core/notify.js";
import { escapeHtml } from "../core/html.js";

/**
 * The dashboard's first page: what visitors did, over a window the owners pick.
 *
 * One request. This page used to make six — two of them for lists it also fetched
 * for their totals — and worked out its numbers in the browser from the whole
 * catalogue, which is why it inherited the API's hundred-row ceiling. The server
 * aggregates now, so the page is a renderer.
 *
 * Every panel has an empty state, and there are two different ones: "nothing has
 * been recorded yet" is not the same as "a quiet week", and a page of zeros that
 * cannot tell you which is a page that looks broken.
 */

const WINDOWS = [7, 30, 90];
const DEFAULT_DAYS = 7;

/** The window from the URL, so a reload and a shared link keep it. */
function chosenDays() {
    const asked = Number(new URLSearchParams(window.location.search).get("dias"));
    return WINDOWS.includes(asked) ? asked : DEFAULT_DAYS;
}

const period = (days) =>
    days === 7 ? "esta semana" : days === 30 ? "neste mês" : `nestes ${days} dias`;

/**
 * The figure's shape over the window, as a line.
 *
 * Hand-rolled SVG rather than a charting library: it is a polyline of at most
 * ninety points with no axes, no labels and no interaction, and the smallest
 * library that draws it is larger than the whole of this file.
 *
 * `viewBox` with `preserveAspectRatio="none"` is what makes it resize with the
 * card: the coordinates below are 0–100 by 0–20 whatever the card's real width
 * turns out to be. Nothing is drawn when there is no shape to show — a flat line
 * along the bottom of every card is decoration, not information.
 */
function sparkline(series) {
    if (!series || series.length < 2) return "";

    const peak = Math.max(...series);
    if (peak === 0) return "";

    const step = 100 / (series.length - 1);
    const points = series
        // SVG's y grows downwards, hence the subtraction; 1 and 19 rather than 0
        // and 20 so the stroke is not clipped at either edge.
        .map((value, index) => `${(index * step).toFixed(1)},${(19 - (value / peak) * 18).toFixed(1)}`)
        .join(" ");

    // mt-auto because the cards are equal height and two of the labels wrap onto a
    // second line: without it their lines sit higher than the rest and the row
    // reads as five unrelated charts.
    return `
      <svg class="mt-auto pt-2" viewBox="0 0 100 20" preserveAspectRatio="none"
           width="100%" height="20" aria-hidden="true" focusable="false">
        <polyline points="${points}" fill="none" stroke="currentColor"
                  stroke-width="1" stroke-linejoin="round" vector-effect="non-scaling-stroke"
                  opacity=".45" />
      </svg>`;
}

/**
 * A figure, how it compares to the window before it, and its shape day by day.
 *
 * The comparison is the point: 62 views means nothing on its own, and "62, up
 * from 50" is a fact somebody can act on. No arrow when the previous window was
 * empty — "up from nothing" is what a first week always looks like. The line
 * underneath says the same thing at a glance, and says where in the window it
 * happened, which no single number can.
 */
function figure(key, label, value, previous, { hasHistory, series }) {
    const delta = value - previous;
    const show = hasHistory && previous > 0 && delta !== 0;
    const tone = delta > 0 ? "--ccg-ready" : "--ccg-attention";

    return `
      <div class="col">
        <div class="card dash-panel p-3 h-100" data-figure="${key}">
          <span class="h4 mb-1 data">${value}</span>
          <span class="eyebrow mb-0">${escapeHtml(label)}</span>
          ${show
              ? `<span class="fs-7 mt-1" style="color: var(${tone})">
                   ${delta > 0 ? "▲" : "▼"} ${Math.abs(delta)} vs. período anterior
                 </span>`
              : `<span class="fs-7 mt-1 text-body-tertiary">&nbsp;</span>`}
          ${sparkline(series)}
        </div>
      </div>`;
}

// The labels say what is actually counted. "Vistas" and "Peças vistas" side by
// side read as the same thing twice, and neither said that what is counted is a
// piece's own page being opened rather than a visit to the site.
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
      <div class="row row-cols-2 row-cols-lg-5 g-2">${cards}</div>
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

/**
 * An empty panel.
 *
 * Two kinds of empty, and they are not the same thing: nothing recorded yet, and
 * a quiet period. The first is said once for the whole page — under the totals,
 * where it belongs — because four panels repeating it is four times the sentence
 * and none of the information. Here it is a dash, which is what "no rows" looks
 * like everywhere else in the dashboard.
 */
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

    // The name links to the piece in the catalogue: the products page reads `q`
    // from the URL, so this needs no deep-linking of its own.
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
    // `added` is null when the window reaches back past the day pieces started
    // being dated, and 0 is nothing to announce — so both leave the phrase out.
    const added = catalogue.added
        ? ` (${catalogue.added} ${catalogue.added === 1 ? "nova" : "novas"})`
        : "";

    const parts = [
        `${catalogue.products} ${catalogue.products === 1 ? "peça" : "peças"}${added}`,
        `${catalogue.color_sets} ${catalogue.color_sets === 1 ? "conjunto de cor" : "conjuntos de cor"}`,
        `${catalogue.collections} ${catalogue.collections === 1 ? "colecção" : "colecções"}`,
        `${catalogue.colors} ${catalogue.colors === 1 ? "cor" : "cores"}`,
    ];

    // Said once, quietly, and only when there is history: on the first day it is
    // the only true thing on the page.
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
    // Replace rather than push: the window is which view of this page you are on,
    // not somewhere you navigated to, so Back should leave the dashboard.
    const url = new URL(window.location.href);
    url.searchParams.set("dias", String(days));
    window.history.replaceState({}, "", url);

    load(days);
});

load(chosenDays());
