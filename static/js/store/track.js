/**
 * What the visitor did, sent to the one endpoint that records it.
 *
 * The dashboard's home page used to be four counters and two lists the owners
 * could already read elsewhere. What it could not say was whether anybody looks
 * at any of it — nothing on the storefront was ever recorded. This is that half.
 *
 * Counters only. Nothing here identifies anybody: no cookie is set, no id is
 * generated, nothing is sent but which piece, which colour, which words. The
 * sessionStorage key below is a browser-local flag so a reload is not a second
 * view; it never leaves the browser and is gone when the tab closes.
 *
 * Failures are swallowed on purpose. A visitor is reading about a wooden box; a
 * counter that could not reach the server is not their problem, and must not put
 * anything in their console.
 */

const ENDPOINT = "/api/storefront-events/";

/** Views already sent in this tab, so a reload does not count twice. */
const SEEN = "ccg-seen";

/** Whether this tab has already been counted as one arrival. */
const ARRIVED = "ccg-arrived";

/**
 * `keepalive` only where the page is about to go away.
 *
 * It is what lets the enquiry survive the navigation to WhatsApp, and it is the
 * reason this is fetch rather than sendBeacon — a beacon cannot set the header
 * the endpoint requires. But Chromium reports a keepalive request the renderer
 * has finished with as ERR_ABORTED even after it answered 204, so using it for a
 * view too puts a failed request in every page check for no benefit: the page is
 * still open when a view is recorded.
 */
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
            // The 204 has no body, but a Response nobody reads is one Chromium
            // aborts when it is collected — which shows up as a failed request on
            // every page check and would hide a real one among them.
            .then((response) => response.text())
            .catch(() => {});
    } catch (error) {
        // Storage disabled, network gone, page tearing down. Nothing to do.
    }
}

/** The pieces this tab has already reported, as a set of ids. */
function seen() {
    try {
        return new Set(JSON.parse(sessionStorage.getItem(SEEN) || "[]"));
    } catch (error) {
        // Private mode, or a value somebody edited by hand.
        return new Set();
    }
}

function remember(productId, ids) {
    try {
        sessionStorage.setItem(SEEN, JSON.stringify([...ids, productId]));
    } catch (error) {
        // Without storage every reload counts again. A slightly high number beats
        // a broken page.
    }
}

export const Track = {
    /**
     * Somebody opened the shop. Once per tab, whichever page they landed on, and
     * carrying nothing — not which page, not where they came from.
     *
     * It is the denominator: eighteen pieces opened reads very differently
     * against twenty arrivals than against two hundred.
     */
    visit() {
        try {
            if (sessionStorage.getItem(ARRIVED)) return;
            sessionStorage.setItem(ARRIVED, "1");
        } catch (error) {
            // Without storage every page load is an arrival. A high number beats
            // no number, and this is the one figure where that is true: the flag
            // is the only thing stopping it, and there is nothing else to use.
        }

        send({ kind: "visit" });
    },

    /**
     * A piece was opened. Once per piece per tab: a reload, or stepping back to
     * it, is the same visit looking at the same thing.
     */
    view(productId) {
        const id = Number(productId);
        if (!id) return;

        const already = seen();
        if (already.has(id)) return;

        remember(id, already);
        send({ kind: "view", product_id: id });
    },

    /**
     * The visitor asked about a piece. Every click counts — asking twice is
     * asking twice — and the colour is the part worth having: it is what tells
     * the owners which colourway to make next.
     */
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
            // The visitor is leaving for WhatsApp as this fires.
            { keepalive: true }
        );
    },

    /**
     * Something was searched for, and how many pieces it found. Only the count of
     * searches is read — the words are stored and nothing shows them, which is
     * how Hugo asked for it.
     */
    search(term, results) {
        const text = String(term || "").trim();
        // One and two letters are somebody still typing.
        if (text.length < 3) return;

        send({ kind: "search", term: text, results: Number(results) || 0 });
    },

    /** A filter was ticked. Only on the way on — unticking is not a preference. */
    filter(facet, label) {
        if (!facet || !label) return;

        send({ kind: "filter", facet: String(facet), facet_label: String(label) });
    },
};
