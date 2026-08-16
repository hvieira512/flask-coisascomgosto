import { API } from "../core/api.js";

const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

/** Every list endpoint answers with a pagination envelope. */
const totalOf = async (url) => {
    const res = await fetch(`${url}?limit=1`);
    if (!res.ok) return 0;
    return (await res.json()).pagination.total;
};

const statCard = ({ label, value, icon, href }) => `
    <a class="cell card p-5 mb-0 dash-stat" href="${href}">
      <span class="dash-stat-icon"><i class="fa-solid ${icon}"></i></span>
      <span class="dash-stat-value">${value}</span>
      <span class="dash-stat-label">${escapeHtml(label)}</span>
    </a>`;

async function renderStats() {
    const [products, types, colorSets, events] = await Promise.all([
        totalOf(API.products.list),
        totalOf(API.productTypes.list),
        totalOf(API.colorSets.list),
        totalOf(API.events.list),
    ]);

    document.getElementById("stat-cards").innerHTML = [
        { label: "Produtos", value: products, icon: "fa-box", href: "/dashboard/products" },
        { label: "Tipos", value: types, icon: "fa-tags", href: "/dashboard/products" },
        { label: "Conjuntos de cor", value: colorSets, icon: "fa-palette", href: "/dashboard/products" },
        { label: "Eventos", value: events, icon: "fa-calendar", href: "/#events" },
    ].map(statCard).join("");
}

/** The one number the owner can act on: pieces the storefront shows as a
    placeholder because nobody has photographed them yet. */
async function renderMissingPhotos() {
    const target = document.getElementById("missing-photos");
    const res = await fetch(`${API.products.list}?limit=100`);
    if (!res.ok) return;

    const { products } = await res.json();
    const missing = products.filter((p) => !p.primary_image);

    target.innerHTML = missing.length
        ? `<ul class="dash-list">${missing
              .map((p) => `<li><a href="/products/${p.id}">${escapeHtml(p.name)}</a>
                    <span class="tag is-light is-rounded">${escapeHtml(p.type?.name ?? "—")}</span></li>`)
              .join("")}</ul>`
        : `<p class="has-text-grey">Todas as peças têm fotografia.</p>`;
}

async function renderEvents() {
    const target = document.getElementById("upcoming-events");
    const res = await fetch(`${API.events.list}?limit=5`);
    if (!res.ok) return;

    const { events } = await res.json();
    target.innerHTML = events.length
        ? `<ul class="dash-list">${events
              .map((e) => `<li><span>${escapeHtml(e.name)}</span>
                    <span class="has-text-grey is-size-7">${escapeHtml(e.starts_on)}</span></li>`)
              .join("")}</ul>`
        : `<p class="has-text-grey">Sem eventos registados.</p>`;
}

renderStats();
renderMissingPhotos();
renderEvents();
