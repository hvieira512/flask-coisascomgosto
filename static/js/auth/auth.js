import { API } from "../core/api.js";
import { removeLoading, renderLoading } from "../core/utils.js";

const container = "#auth-container";

const submitBtn = document.querySelector("#submitBtn");
const usernameField = document.querySelector("#usernameField");
const formHeader = document.querySelector("#form-header");
const form = document.querySelector("#auth-form");

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const mode = submitBtn.dataset.mode || "check";

    const username = usernameField.value.trim();
    if (!username) return;

    if (mode === "check") {
        renderLoading(container);
        const res = await fetch(API.auth.login, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifier: username, password: "fake" })
        });
        removeLoading(container);

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

        renderLoading(container);
        const res = await fetch(API.auth.login, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifier: username, password })
        });
        removeLoading(container);

        if (!res.ok) {
            const data = await res.json();
            toastr.error(data.error || "Login falhou");
        }

        toastr.success("Login realizado com sucesso.")
        window.location.href = "/dashboard";
    }

    if (mode === "register") {
        const email = document.querySelector("#emailField")?.value.trim();
        const department = document.querySelector("#departmentsField")?.value;
        const password = document.querySelector("#passwordField")?.value.trim();
        const confirm = document.querySelector("#confirmPasswordField")?.value.trim();

        if (!password || password !== confirm) {
            toastr.error("As passwords não coincidem.");
            return;
        }

        renderLoading(container);
        const res = await fetch(API.auth.register, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password, department })
        });
        removeLoading(container);

        if (!res.ok) {
            const data = await res.json();
            toastr.error(data.error || "Registo falhou.");
            return;
        }

        const login_res = await fetch(API.auth.login, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifier: email, password })
        });

        if (!login_res.ok) {
            const data = await login_res.json();
            toastr.error(data.error || "Login falhou.");
            return;
        }

        toastr.success("Login realizado com sucesso.");
        window.location.href = "/dashboard";
    }
});

function renderLoginForm(username) {
    formHeader.innerHTML = `
        <h1 class="h2 mb-0">Olá, ${username}!</h1>
        <p class="text-dark">Introduz a tua password para entrar.</p>
    `;
    appendInput({ icon: 'fa-lock', type: 'password', id: 'passwordField', name: 'password', placeholder: 'Password' });
    document.querySelector("#passwordField").focus();
}

async function renderRegisterForm(username) {
    formHeader.innerHTML = `
        <h1 class="h2 mb-0">Olá, ${username}!</h1>
        <p class="text-dark">Define a tua palavra-passe para continuares.</p>
    `;

    appendInput({ icon: 'fa-at', type: 'email', id: 'emailField', name: 'email', placeholder: 'E-mail' });
    document.querySelector("#emailField").value = `${username}@borgwarner.com`;

    appendInput({ icon: 'fa-lock', type: 'password', id: 'passwordField', name: 'password', placeholder: 'Password' });
    appendInput({ icon: 'fa-lock', type: 'password', id: 'confirmPasswordField', name: 'confirmPassword', placeholder: 'Confirmar Password' });
}

function appendInput({ icon, type, id, name, placeholder }) {
    if (document.querySelector(`#${id}`)) return;

    const group = document.createElement("div");
    group.className = "input-group";

    group.innerHTML = `
        <span class="input-group-text p-3 rounded-start">
            <i class="fa-solid ${icon}"></i>
        </span>
        <input type="${type}" class="form-control rounded-end p-3" placeholder="${placeholder}" name="${name}" id="${id}" required />
    `;

    submitBtn.parentNode.insertBefore(group, submitBtn);
}
