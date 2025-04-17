import { API, postData } from "../core/api.js";

const form = document.getElementById("auth-form");
const usernameInput = document.getElementById("username");
const passwordWrapper = document.getElementById("password-wrapper");
const passwordInput = document.getElementById("password");
const submitBtn = document.getElementById("submit-btn");
const title = document.getElementById("form-title");

let mode = "login";

usernameInput.addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        const username = usernameInput.value.trim();

        if (!username) {
            alert("Username is required.");
            return;
        }

        try {
            await postData(API.auth.login, { username, password: "fake" });
            mode = "login";
            title.textContent = "Login";
        } catch (err) {
            if (err.message === "Invalid login.") {
                // If login fails, consider it as login
                mode = "login";
                title.textContent = "Login";
            } else {
                // If error occurs, assume it's a registration case
                mode = "register";
                title.textContent = "Register";
            }
        }

        showPassword();
    }
});

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
        alert("Username and password are required.");
        return;
    }

    try {
        const endpoint = mode === "login" ? API.auth.login : API.auth.register;
        const data = { username, password };

        if (mode === "register") {
            data.email = `${username}@placeholder.com`; // Dummy email for registration
        }

        const res = await postData(endpoint, data);
        console.error(res);
        window.location.href = "/dashboard"; // Redirect to the dashboard or another protected page
    } catch (err) {
        alert(err.message);
    }
});

function showPassword() {
    passwordWrapper.classList.remove("d-none");  // Correcting classList to classList
    submitBtn.classList.remove("d-none");  // Correcting classList to classList
    passwordInput.focus();
}

