import { API } from "../core/api.js";
import { Notify } from "../core/notify.js";
import { fieldIcon } from "../core/html.js";

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
            body: JSON.stringify({ username, password: "fake" }),
        });
        submitBtn.classList.remove("is-loading");

        switch (res.status) {
            case 401:
                submitBtn.dataset.mode = "login";
                renderLoginForm(username);
                break;
            case 404:
                submitBtn.dataset.mode = "register";
                await renderRegisterForm(username);
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

    if (mode === "register") {
        const username = document.querySelector("#usernameField")?.value;
        const email = document.querySelector("#emailField")?.value.trim();
        const password = document.querySelector("#passwordField")?.value.trim();
        const confirm = document
            .querySelector("#confirmPasswordField")
            ?.value.trim();

        if (!password || password !== confirm) {
            Notify.error("As passwords não coincidem.");
            return;
        }

        submitBtn.classList.add("is-loading");
        const res = await fetch(API.auth.register, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, password }),
        });
        submitBtn.classList.remove("is-loading");

        if (!res.ok) {
            const data = await res.json();
            Notify.error(data.error || "Registo falhou.");
            return;
        }

        const login_res = await fetch(API.auth.login, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });

        if (!login_res.ok) {
            const data = await login_res.json();
            Notify.error(data.message || "Login falhou.");
            return;
        }

        Notify.success("Login realizado com sucesso.");
        window.location.href = "/dashboard";
    }
});

function renderLoginForm(username) {
    formHeader.innerHTML = `
        <h1 class="h4 mb-1">Olá, ${username}!</h1>
        <p class="text-body-secondary">Introduz a tua password para entrar.</p>
    `;
    appendInput({
        icon: "fa-lock",
        type: "password",
        id: "passwordField",
        name: "password",
        placeholder: "Password",
    });
    document.querySelector("#passwordField").focus();
}

async function renderRegisterForm(username) {
    formHeader.innerHTML = `
        <h1 class="h4 mb-1">Olá, ${username}!</h1>
        <p class="text-body-secondary">Define a tua palavra-passe para continuares.</p>
    `;

    appendInput({
        icon: "fa-at",
        type: "email",
        id: "emailField",
        name: "email",
        placeholder: "E-mail",
    });
    appendInput({
        icon: "fa-lock",
        type: "password",
        id: "passwordField",
        name: "password",
        placeholder: "Password",
    });
    appendInput({
        icon: "fa-lock",
        type: "password",
        id: "confirmPasswordField",
        name: "confirmPassword",
        placeholder: "Confirmar Password",
    });

    document.querySelector("#emailField").focus();
}

function appendInput({ icon, type, id, name, placeholder }) {
    if (document.querySelector(`#${id}`)) return;

    const field = document.createElement("div");
    field.className = "mb-3";

    field.innerHTML = `
        <div class="input-group input-group-lg">
            <input type="${type}" class="form-control form-control-lg" placeholder="${placeholder}"
                   name="${name}" id="${id}" required>
            ${fieldIcon(`fa-solid ${icon}`)}
        </div>
    `;

    // Insert above the row the submit button sits in.
    const anchor = submitBtn.parentElement;
    anchor.parentNode.insertBefore(field, anchor);
}
