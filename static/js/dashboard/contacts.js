import { API } from "../core/api.js";
import { submitting } from "../core/modal.js";

/**
 * The shop's contact details. A singleton — one row, edited in place, so there
 * is no create or delete, and the page is a form rather than a list.
 */
const FIELDS = [
    "address", "maps_url", "email", "whatsapp", "facebook_url", "instagram_url",
];

const field = (name) => document.getElementById(`cf-${name}`);
let saved = {};

/** wa.me takes digits only — the same rule the API applies. */
const whatsappUrl = (number) => {
    const digits = String(number ?? "").replace(/\D/g, "");
    return digits ? `https://wa.me/${digits}` : "";
};

function renderPreview() {
    const cards = [
        { label: "Morada", value: field("address").value, icon: "fa-solid fa-location-dot" },
        { label: "E-mail", value: field("email").value, icon: "fa-solid fa-envelope" },
        { label: "WhatsApp", value: field("whatsapp").value, icon: "fa-brands fa-whatsapp" },
        { label: "Facebook", value: field("facebook_url").value, icon: "fa-brands fa-facebook-f" },
        { label: "Instagram", value: field("instagram_url").value, icon: "fa-brands fa-instagram" },
    ].filter((card) => card.value.trim());

    document.getElementById("contact-preview").innerHTML = cards.length
        ? `<ul class="dash-rows is-flex is-flex-direction-column">${cards.map((card) => `
             <li class="dash-row">
               <span class="disc contact-icon mr-3"><i class="${card.icon}"></i></span>
               <span class="eyebrow mb-0">${escapeHtml(card.label)}</span>
             </li>`).join("")}</ul>`
        : `<p class="has-text-grey is-size-7">Sem contactos preenchidos.</p>`;

    const number = field("whatsapp").value;
    document.getElementById("cf-whatsapp-preview").textContent =
        number ? `Abre ${whatsappUrl(number)}` : "Só dígitos; o link wa.me é gerado.";
}

function fill(contact) {
    FIELDS.forEach((name) => {
        field(name).value = contact[name] ?? "";
    });
    renderPreview();
}

async function load() {
    const res = await fetch(API.contacts.get);
    if (!res.ok) {
        Notify.error("Erro ao carregar os contactos.");
        return;
    }
    saved = await res.json();
    fill(saved);
}

function save(event) {
    event.preventDefault();

    return submitting(document.getElementById("contact-save"), async () => {
        // PUT replaces the whole row: a field left out is cleared, so every
        // field is always sent. Empty ones are omitted deliberately — that is
        // how a detail is removed — and the API rejects an explicit null.
        const payload = {};
        FIELDS.forEach((name) => {
            const value = field(name).value.trim();
            if (value) payload[name] = value;
        });

        const res = await fetch(API.contacts.update, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.message || "Não foi possível guardar.");
        }

        saved = await res.json();
        fill(saved);
        Notify.success("Contactos actualizados.");
    });
}

document.getElementById("contact-form").addEventListener("submit", save);
document.getElementById("contact-form").addEventListener("input", renderPreview);
document.getElementById("contact-reset").addEventListener("click", () => fill(saved));

load();
