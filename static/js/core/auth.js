/**
 * Bearer-token handling for the browser.
 *
 * Tokens are kept in localStorage. `authFetch` attaches the access token and,
 * when the API answers 401 because the access token expired, transparently
 * exchanges the refresh token at /api/auth/refresh and retries the original
 * request once. Only if the refresh itself fails is the user sent back to the
 * login page.
 *
 * Concurrent 401s share a single in-flight refresh, so a page firing several
 * requests at once does not mint several tokens.
 */
window.Auth = (function () {
    const ACCESS_KEY = "ccg.access_token";
    const REFRESH_KEY = "ccg.refresh_token";

    let refreshInFlight = null;

    function getAccessToken() {
        return localStorage.getItem(ACCESS_KEY);
    }

    function getRefreshToken() {
        return localStorage.getItem(REFRESH_KEY);
    }

    function store({ access_token, refresh_token }) {
        if (access_token) localStorage.setItem(ACCESS_KEY, access_token);
        if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
    }

    function clear() {
        localStorage.removeItem(ACCESS_KEY);
        localStorage.removeItem(REFRESH_KEY);
    }

    function isAuthenticated() {
        return Boolean(getAccessToken());
    }

    /** Exchange username/password for a token pair. */
    async function login(username, password) {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
            const error = new Error("Login failed");
            error.status = response.status;
            throw error;
        }

        const tokens = await response.json();
        store(tokens);
        return tokens;
    }

    /**
     * Swap the refresh token for a new access token.
     * Returns null when the refresh token is missing or itself rejected.
     */
    async function refresh() {
        const refreshToken = getRefreshToken();
        if (!refreshToken) return null;

        // Collapse parallel refreshes into one request.
        if (!refreshInFlight) {
            refreshInFlight = fetch("/api/auth/refresh", {
                method: "POST",
                headers: { Authorization: `Bearer ${refreshToken}` },
            })
                .then((response) => (response.ok ? response.json() : null))
                .then((tokens) => {
                    if (tokens?.access_token) {
                        store(tokens);
                        return tokens.access_token;
                    }
                    clear();
                    return null;
                })
                .catch(() => {
                    clear();
                    return null;
                })
                .finally(() => {
                    refreshInFlight = null;
                });
        }

        return refreshInFlight;
    }

    /**
     * Statuses that mean "this access token is unusable, try to replace it".
     *
     * flask-jwt-extended answers 401 for an *expired* token but 422 for a
     * *malformed* one — which is what a truncated localStorage value or a
     * rotated signing key produces. Retrying only on 401 would leave the
     * client wedged on a corrupt token with no way back to the login page.
     */
    const TOKEN_REJECTED = new Set([401, 422]);

    /** fetch() with the bearer token attached and one automatic retry. */
    async function authFetch(url, options = {}) {
        const request = (token) => {
            const headers = new Headers(options.headers || {});
            if (token) headers.set("Authorization", `Bearer ${token}`);
            return fetch(url, { ...options, headers });
        };

        let response = await request(getAccessToken());
        if (!TOKEN_REJECTED.has(response.status)) return response;

        const fresh = await refresh();
        if (!fresh) {
            onSessionExpired();
            return response;
        }

        response = await request(fresh);
        if (TOKEN_REJECTED.has(response.status)) onSessionExpired();
        return response;
    }

    /** Overridable hook: what to do once the refresh token is dead too. */
    let onSessionExpired = () => {
        clear();
        if (!window.location.pathname.startsWith("/auth")) {
            window.location.href = "/auth";
        }
    };

    return {
        login,
        storeTokens: store,
        logout: clear,
        refresh,
        authFetch,
        isAuthenticated,
        getAccessToken,
        getRefreshToken,
        setSessionExpiredHandler(fn) {
            onSessionExpired = fn;
        },
    };
})();
