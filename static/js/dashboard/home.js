import { API } from "../core/api.js";
import { daysUntil, eventState, shortDate, stateChip } from "./events/dates.js";

/** Every list endpoint answers with a pagination envelope. */
const totalOf = async (url) => {
    const res = await fetch(`${url}?limit=1`);
    if (!res.ok) return 0;
    return (await res.json()).pagination.total;
};

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
      <a class="cell card p-4 mb-0 has-text-inherit is-flex is-gap-2 is-align-items-flex-start"
         href="${href}">
        <span class="icon" style="color: var(--ccg-${tone})">
          <i class="fa-solid ${icon}"></i>
        </span>
        <span class="is-flex is-flex-direction-column">
          <span class="has-text-weight-semibold">${headline}</span>
          <span class="is-size-7 has-text-grey">${detail}</span>
          <span class="is-size-7 mt-2" style="color: var(--ccg-blue-600)">${action} →</span>
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
        ? `<div class="grid is-col-min-16">${cards.join("")}</div>`
        : `<div class="card dash-panel p-4 is-flex is-gap-2 is-align-items-center">
             <span class="icon" style="color: var(--ccg-ready)">
               <i class="fa-solid fa-circle-check"></i>
             </span>
             <span>Nada à espera. O catálogo está completo e sem eventos por abrir.</span>
           </div>`;
}

const statCard = ({ label, value, href }) => `
    <a class="cell card p-4 mb-0 is-flex is-flex-direction-column has-text-inherit"
       href="${href}">
      <span class="title is-4 mb-1">${value}</span>
      <span class="eyebrow mb-0">${escapeHtml(label)}</span>
    </a>`;

async function renderStats() {
    const [products, types, colorSets, events] = await Promise.all([
        totalOf(API.products.list),
        totalOf(API.productTypes.list),
        totalOf(API.colorSets.list),
        totalOf(API.events.list),
    ]);

    document.getElementById("stat-cards").innerHTML = [
        { label: "Peças", value: products, href: "/dashboard/products" },
        { label: "Tipos", value: types, href: "/dashboard/products" },
        { label: "Conjuntos de cor", value: colorSets, href: "/dashboard/products" },
        { label: "Eventos", value: events, href: "/dashboard/events" },
    ].map(statCard).join("");
}

function renderMissingPhotos(products) {
    const missing = products.filter((p) => photoCount(p) === 0);

    document.getElementById("missing-photos").innerHTML = missing.length
        ? `<ul class="panel is-shadowless mb-0">${missing
              .map((p) => `
                <li class="panel-block px-0 is-justify-content-space-between">
                  <a href="/dashboard/products">${escapeHtml(p.name)}</a>
                  <span class="tag is-rounded chip is-quiet">
                    ${escapeHtml(p.type?.name ?? p.category.name)}
                  </span>
                </li>`)
              .join("")}</ul>`
        : `<p class="has-text-grey is-size-7">Todas as peças têm fotografia.</p>`;
}

function renderEvents(events) {
    const sorted = [...events].sort((a, b) => b.starts_on.localeCompare(a.starts_on));

    document.getElementById("upcoming-events").innerHTML = sorted.length
        ? `<ul class="panel is-shadowless mb-0">${sorted
              .slice(0, 5)
              .map((e) => {
                  return `
                    <li class="panel-block px-0 is-justify-content-space-between">
                      <span>
                        ${escapeHtml(e.name)}
                        ${stateChip(e, { extraClass: "ml-2" })}
                      </span>
                      <span class="data has-text-grey">${escapeHtml(shortDate(e.starts_on))}</span>
                    </li>`;
              })
              .join("")}</ul>`
        : `<p class="has-text-grey is-size-7">Sem eventos registados.</p>`;
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
