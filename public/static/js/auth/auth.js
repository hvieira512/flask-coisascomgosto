import { API } from "../core/api.js";
import { Notify } from "../core/notify.js";
import { escapeHtml } from "../core/html.js";

const submitBtn = document.querySelector("#submitBtn");
const usernameField = document.querySelector("#usernameField");
const formHeader = document.querySelector("#form-header");
const form = document.querySelector("#auth-form");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const mode = submitBtn.dataset.mode || "check";

    const username = usernameField.value.trim();
    if (!username) return;

    if (mode === "check") {
        submitBtn.classList.add("is-loading");
        const res = await fetch(API.auth.login, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username }),
        });
        submitBtn.classList.remove("is-loading");

        switch (res.status) {
            case 401:
                submitBtn.dataset.mode = "login";
                renderLoginForm(username);
                break;
            case 404:
                Notify.error("Não há nenhuma conta com esse nome.");
                break;
            case 429:
                Notify.error((await res.json()).message);
                break;
            default:
                console.error("Unexpected response:", res);
                break;
        }
    }

    if (mode === "login") {
        const password = document.querySelector("#passwordField")?.value.trim();
        if (!password) return;

        submitBtn.classList.add("is-loading");
        const res = await fetch(API.auth.login, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        submitBtn.classList.remove("is-loading");

        if (!res.ok) {
            const data = await res.json();
            Notify.error(data.message || "Login falhou");
            return;
        }

        Notify.success("Login realizado com sucesso.");
        window.location.href = "/dashboard";
    }
});

function renderLoginForm(username) {
    formHeader.innerHTML = `
        <p class="eyebrow">Área reservada</p>
        <h1 class="h2 font-display mb-2">Olá, ${escapeHtml(username)}!</h1>
        <p class="text-body-secondary mb-0">Introduza a sua palavra-passe para entrar.</p>
    `;
    appendPasswordField();
    submitBtn.querySelector("span").textContent = "Entrar";
    document.querySelector("#passwordField").focus();
}

function appendPasswordField() {
    if (document.querySelector("#passwordField")) return;

    const field = document.createElement("div");
    field.className = "mb-3";
    field.innerHTML = `
        <label class="form-label" for="passwordField">Palavra-passe</label>
        <input type="password" class="form-control form-control-lg" name="password"
               id="passwordField" autocomplete="current-password" required>
    `;

    const anchor = submitBtn.parentElement;
    anchor.parentNode.insertBefore(field, anchor);
}
