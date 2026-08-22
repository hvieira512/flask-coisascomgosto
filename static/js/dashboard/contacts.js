import { API, request } from "../core/api.js";
import { Notify } from "../core/notify.js";
import { escapeHtml } from "../core/html.js";
import { submitting } from "../core/modal.js";

const FIELDS = [
    "address", "maps_url", "email", "whatsapp", "facebook_url", "instagram_url",
];

const field = (name) => document.getElementById(`cf-${name}`);
let saved = {};

const whatsappUrl = (number) => {
    const digits = String(number ?? "").replace(/\D/g, "");
    return digits ? `https://wa.me/${digits}` : "";
};

const socialHandle = (url) => {
    const path = String(url ?? "").replace(/^https?:\/\/[^/]+/i, "").split("?")[0];
    const handle = path.replace(/^\/+|\/+$/g, "").split("/").pop();
    return handle || url;
};

function renderPreview() {
    const cards = [
        { label: "Morada", value: field("address").value, icon: "fa-solid fa-location-dot" },
        { label: "E-mail", value: field("email").value, icon: "fa-solid fa-envelope" },
        { label: "WhatsApp", value: field("whatsapp").value, icon: "fa-brands fa-whatsapp" },
        { label: "Facebook", value: socialHandle(field("facebook_url").value), icon: "fa-brands fa-facebook-f" },
        { label: "Instagram", value: socialHandle(field("instagram_url").value), icon: "fa-brands fa-instagram" },
    ].filter((card) => card.value.trim());

    document.getElementById("contact-preview").innerHTML = cards.length
        ? `<ul class="list-group list-group-flush">${cards.map((card) => `
             <li class="list-group-item d-flex align-items-center px-0">
               <span class="disc contact-icon me-3"><i class="${card.icon}"></i></span>
               <span class="contact-body">
                 <span class="eyebrow mb-0">${escapeHtml(card.label)}</span>
                 <span class="contact-value">${escapeHtml(card.value.trim())}</span>
               </span>
             </li>`).join("")}</ul>`
        : `<p class="text-body-secondary fs-7">Sem contactos preenchidos.</p>`;

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
    try {
        saved = await request(API.contacts.get,
                             { fallback: "Erro ao carregar os contactos." });
    } catch (error) {
        Notify.error(error.message);
        return;
    }
    fill(saved);
}

function save(event) {
    event.preventDefault();

    return submitting(document.getElementById("contact-save"), async () => {
        const payload = {};
        FIELDS.forEach((name) => {
            const value = field(name).value.trim();
            if (value) payload[name] = value;
        });

        saved = await request(API.contacts.update, {
            method: "PUT",
            body: payload,
            fallback: "Não foi possível guardar.",
        });
        fill(saved);
        Notify.success("Contactos actualizados.");
    });
}

document.getElementById("contact-form").addEventListener("submit", save);
document.getElementById("contact-form").addEventListener("input", renderPreview);
document.getElementById("contact-reset").addEventListener("click", () => fill(saved));

load();
