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
    const address = field("address").value.trim();
    const rows = [
        ["WhatsApp", field("whatsapp").value],
        ["E-mail", field("email").value],
        ["Instagram", socialHandle(field("instagram_url").value)],
        ["Facebook", socialHandle(field("facebook_url").value)],
    ].filter(([, value]) => String(value ?? "").trim());

    document.getElementById("contact-preview").innerHTML = address || rows.length
        ? `<div class="bg-body text-body rounded-3 p-4" data-bs-theme="dark">
             <p class="eyebrow">Contactos</p>
             <p class="font-display fs-4 fw-semibold mb-2">Onde nos encontra</p>
             ${address ? `<p class="font-display fs-6 mb-3">${escapeHtml(address)}</p>` : ""}
             <dl class="mb-0 fs-7">${rows.map(([label, value]) => `
               <div class="row gx-2 border-top py-2">
                 <dt class="col-4 fw-semibold text-uppercase text-body-secondary">${escapeHtml(label)}</dt>
                 <dd class="col-8 mb-0">${escapeHtml(String(value).trim())}</dd>
               </div>`).join("")}</dl>
           </div>`
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
