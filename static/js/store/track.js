const ENDPOINT = "/api/storefront-events/";

const SEEN = "ccg-seen";

const ARRIVED = "ccg-arrived";

function send(body, { keepalive = false } = {}) {
    try {
        fetch(ENDPOINT, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "fetch",
            },
            body: JSON.stringify(body),
            keepalive,
        })
            // Chromium aborts a 204 whose body nobody reads, which shows up as a
            // failed request on every page check.
            .then((response) => response.text())
            .catch(() => {});
    } catch (error) {
        // Swallowed: a visitor reading about a wooden box must not get a counter's
        // failure in their console.
    }
}

function seen() {
    try {
        return new Set(JSON.parse(sessionStorage.getItem(SEEN) || "[]"));
    } catch (error) {
        return new Set();
    }
}

function remember(productId, ids) {
    try {
        sessionStorage.setItem(SEEN, JSON.stringify([...ids, productId]));
    } catch (error) {
        // Swallowed: a visitor reading about a wooden box must not get a counter's
        // failure in their console.
    }
}

export const Track = {
    visit() {
        try {
            if (sessionStorage.getItem(ARRIVED)) return;
            sessionStorage.setItem(ARRIVED, "1");
        } catch (error) {
        }

        send({ kind: "visit" });
    },

    view(productId) {
        const id = Number(productId);
        if (!id) return;

        const already = seen();
        if (already.has(id)) return;

        remember(id, already);
        send({ kind: "view", product_id: id });
    },

    enquiry({ productId, variantId = null, sizeId = null }) {
        const id = Number(productId);
        if (!id) return;

        send(
            {
                kind: "enquiry",
                product_id: id,
                ...(variantId ? { variant_id: Number(variantId) } : {}),
                ...(sizeId ? { size_id: Number(sizeId) } : {}),
            },
            { keepalive: true }
        );
    },

    search(term, results) {
        const text = String(term || "").trim();
        if (text.length < 3) return;

        send({ kind: "search", term: text, results: Number(results) || 0 });
    },

    filter(facet, label) {
        if (!facet || !label) return;

        send({ kind: "filter", facet: String(facet), facet_label: String(label) });
    },
};
