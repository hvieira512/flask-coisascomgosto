export const request = async (method, url, payload = null) => {
    let options = { method, headers: {} };

    if (payload !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(payload);
    }

    let res;
    try {
        res = await fetch(url, options);
    } catch {
        throw new Error("Erro de rede: não foi possível contactar o servidor.");
    }

    let data;
    try {
        data = await res.json();
    } catch {
        data = { error: "Resposta inválida do servidor." };
    }

    if (!res.ok)
        throw new Error(data.error || data.message || "Erro desconhecido.");
    return data;
};

export const get = async (url, params = {}) => {
    const hasParams = Object.keys(params).length > 0;
    const query = hasParams ? `?${new URLSearchParams(params)}` : "";
    return request("GET", `${url}${query}`);
};

export const post = async (url, payload) => request("POST", url, payload);
export const put = async (url, payload) => request("PUT", url, payload);
export const patch = async (url, payload) => request("PATCH", url, payload);
export const del = async (url, payload) => request("DELETE", url, payload);
