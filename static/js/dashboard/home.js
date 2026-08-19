import { API, requestOr } from "../core/api.js";
import { Notify } from "../core/notify.js";
import { daysUntil, eventState, shortDate, stateChip } from "./events/dates.js";
import { escapeHtml } from "../core/html.js";

/** Every list endpoint answers with a pagination envelope. A card that cannot be
 *  counted shows nothing rather than taking the whole page down with it. */
const totalOf = async (url) =>
    (await requestOr(`${url}?limit=1`, { pagination: { total: 0 } })).pagination.total;

/** Photographs live on the product and on each variant. */
const photoCount = (product) =>
    (product.images ?? []).length
    + product.variants.reduce((n, v) => n + (v.images ?? []).length, 0);

const dayLabel = (days) => {
    if (days === 1) return "amanhã";
    return `em ${days} dias`;
};

/**
 * The attention strip: one card per thing actually waiting on someone, and
 * nothing at all when there is nothing to do. Counting the pieces without a
 * photograph and the fair that is about to open is the whole reason to open
 * this page — a row of totals is not.
 */
function attentionCard({ tone, icon, headline, detail, href, action }) {
    return `
      <a class="card p-3 flex-row gap-2 align-items-start text-body text-decoration-none"
         href="${href}">
        <span class="icon" style="color: var(--ccg-${tone})">
          <i class="fa-solid ${icon}"></i>
        </span>
        <span class="d-flex flex-column">
          <span class="fw-semibold">${headline}</span>
          <span class="fs-7 text-body-secondary">${detail}</span>
          <span class="fs-7 mt-2" style="color: var(--ccg-blue-600)">${action} →</span>
        </span>
      </a>`;
}

async function renderAttention(products, events) {
    const cards = [];

    const missing = products.filter((p) => photoCount(p) === 0);
    if (missing.length) {
        cards.push(attentionCard({
            tone: "attention",
            icon: "fa-camera",
            headline: `${missing.length} ${missing.length === 1 ? "peça" : "peças"} sem fotografia`,
            detail: "A loja mostra um marcador de cor no lugar da fotografia.",
            href: "/dashboard/products?fotos=none",
            action: "Ver as peças",
        }));
    }

    // Only a fair that has not finished is worth flagging; the storefront
    // timeline keeps the rest.
    const live = events
        .filter((e) => eventState(e) !== "past")
        .sort((a, b) => a.starts_on.localeCompare(b.starts_on));

    if (live.length) {
        const next = live[0];
        const running = eventState(next) === "running";

        cards.push(attentionCard({
            tone: running ? "ready" : "blue-600",
            icon: "fa-calendar-day",
            headline: running
                ? "A decorrer agora"
                : `Próximo evento ${dayLabel(daysUntil(next))}`,
            detail: `${escapeHtml(next.name)}${next.location ? ` · ${escapeHtml(next.location)}` : ""}`,
            href: "/dashboard/events",
            action: "Ver eventos",
        }));
    }

    // Auto-fit rather than a fixed two columns: with one thing waiting, a card
    // in half a row reads as a card with something missing beside it.
    document.getElementById("attention").innerHTML = cards.length
        ? `<div class="dash-attention-grid">${cards.join("")}</div>`
        : `<div class="card dash-panel p-3 flex-row gap-2 align-items-center">
             <span class="icon" style="color: var(--ccg-ready)">
               <i class="fa-solid fa-circle-check"></i>
             </span>
             <span>Nada à espera. O catálogo está completo e sem eventos por abrir.</span>
           </div>`;
}

/**
 * A counter is only a link when there is somewhere to go. Colour sets have no
 * page of their own — they are attached to a piece from its Cores tab — so that
 * card renders as plain text rather than promising a destination.
 */
const statCard = ({ label, value, href }) => {
    const inner = `
      <span class="h4 mb-1">${value}</span>
      <span class="eyebrow mb-0">${escapeHtml(label)}</span>`;

    return href
        ? `<a class="card p-3 text-body text-decoration-none" href="${href}">${inner}</a>`
        : `<div class="card p-3">${inner}</div>`;
};

async function renderStats() {
    const [products, types, colorSets, events] = await Promise.all([
        totalOf(API.products.list),
        totalOf(API.productTypes.list),
        totalOf(API.colorSets.list),
        totalOf(API.events.list),
    ]);

    document.getElementById("stat-cards").innerHTML = [
        { label: "Peças", value: products, href: "/dashboard/products" },
        { label: "Tipos", value: types, href: "/dashboard/types" },
        { label: "Conjuntos de cor", value: colorSets },
        { label: "Eventos", value: events, href: "/dashboard/events" },
    ].map(statCard).join("");
}

function renderMissingPhotos(products) {
    const missing = products.filter((p) => photoCount(p) === 0);

    document.getElementById("missing-photos").innerHTML = missing.length
        ? `<ul class="list-group list-group-flush">${missing
              .map((p) => `
                <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                  <a href="/dashboard/products">${escapeHtml(p.name)}</a>
                  <span class="badge rounded-pill chip is-quiet">
                    ${escapeHtml(p.type.name)}
                  </span>
                </li>`)
              .join("")}</ul>`
        : `<p class="text-body-secondary fs-7">Todas as peças têm fotografia.</p>`;
}

function renderEvents(events) {
    const sorted = [...events].sort((a, b) => b.starts_on.localeCompare(a.starts_on));

    document.getElementById("upcoming-events").innerHTML = sorted.length
        ? `<ul class="list-group list-group-flush">${sorted
              .slice(0, 5)
              .map((e) => {
                  return `
                    <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                      <span>
                        ${escapeHtml(e.name)}
                        ${stateChip(e, { extraClass: "ms-2" })}
                      </span>
                      <span class="data text-body-secondary">${escapeHtml(shortDate(e.starts_on))}</span>
                    </li>`;
              })
              .join("")}</ul>`
        : `<p class="text-body-secondary fs-7">Sem eventos registados.</p>`;
}

/** One request for each list, shared by the strip and the panels below it. */
async function load() {
    const [productsRes, eventsRes] = await Promise.all([
        fetch(`${API.products.list}?limit=100`),
        fetch(`${API.events.list}?limit=100`),
    ]);
    if (!productsRes.ok || !eventsRes.ok) {
        Notify.error("Erro ao carregar o painel.");
        return;
    }

    const { products } = await productsRes.json();
    const { events } = await eventsRes.json();

    renderAttention(products, events);
    renderMissingPhotos(products);
    renderEvents(events);
}

renderStats();
load();
