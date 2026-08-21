"""The one HTTP layer the front end talks through, exercised in a real browser.

`static/js/core/api.js` is loaded as a module from the running app and driven
with `window.fetch` replaced, so these are the shipped functions answering an
envelope of our choosing — no second implementation to keep in step.

What is being pinned down is the ceiling. Every dashboard screen works out its
counts and filters from a list it believes is complete: pieces per type, per
collection and per colour set, and "sem fotografia", none of which any endpoint
computes. The API caps `limit` at 100, so at 101 products all of those numbers
quietly shrink and the `?fotos=none` link shows a subset. Nothing errors. These
tests are what makes that arrive as a failure instead.

`live_server` and `browser` come from conftest.py.
"""

import pytest

pytest.importorskip("playwright.sync_api")

# 101 records answered 100 at a time — one over the API's own ceiling, which is
# where every count on the dashboard starts lying.
OVER_THE_CEILING = {
    "products": [{"id": n} for n in range(100)],
    "pagination": {"total": 101, "page": 1, "limit": 100, "pages": 2},
}

WHOLE_LIST = {
    "products": [{"id": n} for n in range(14)],
    "pagination": {"total": 14, "page": 1, "limit": 100, "pages": 1},
}


@pytest.fixture()
def api(browser, live_server):
    """A page holding the real module, with fetch under our control.

    Any dashboard page would do; /auth is the one that needs no session.
    """
    page = browser.new_page()
    page.goto(f"{live_server}/auth")

    def run(script, envelope):
        """Answer every fetch with `envelope`, then evaluate `script`.

        The script is the body of an async function with `api` in scope, and
        returns either its value or the message of whatever it threw — the
        thing under test is a refusal, and a thrown Error does not survive
        the trip out of the browser.
        """
        return page.evaluate(
            """async ([script, envelope]) => {
                window.fetch = async () => new Response(JSON.stringify(envelope), {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                });
                const api = await import("/static/js/core/api.js");
                try {
                    return { value: await new Function("api", `return (async () => {
                        ${script}
                    })()`)(api) };
                } catch (error) {
                    return { error: error.message, truncated: error.truncated === true };
                }
            }""",
            [script, envelope],
        )

    yield run
    page.close()


class TestATruncatedListIsRefused:
    def test_request_throws_naming_the_endpoint_and_the_numbers(self, api):
        result = api("return await api.request('/api/products/');", OVER_THE_CEILING)

        assert "error" in result, result
        assert "/api/products/" in result["error"]
        # The two numbers are the whole diagnosis: what we got, what exists.
        assert "100" in result["error"] and "101" in result["error"]

    def test_the_message_says_what_to_do_about_it(self, api):
        """A message that only says "truncated" leaves the next reader guessing at
        the fix, which is a server-side filter or real pagination."""
        result = api("return await api.request('/api/products/');", OVER_THE_CEILING)

        assert "pagination" in result["error"]

    def test_list_throws_too(self, api):
        result = api(
            "return await api.list(api.API.products.list, 'products');",
            OVER_THE_CEILING,
        )

        assert "error" in result, result

    def test_or_empty_does_not_swallow_it(self, api):
        """`orEmpty` is for a lookup that failed to arrive, where an empty filter
        bar beats an error. A truncated list is a wrong answer, not a missing
        one, and swallowing it is what kept this invisible."""
        result = api(
            "return await api.list(api.API.products.list, 'products', { orEmpty: true });",
            OVER_THE_CEILING,
        )

        assert "error" in result, result
        assert result["truncated"] is True

    def test_request_or_does_not_swallow_it_either(self, api):
        result = api(
            "return await api.requestOr('/api/products/', { products: [] });",
            OVER_THE_CEILING,
        )

        assert "error" in result, result


class TestWhatMustKeepWorking:
    def test_a_complete_list_passes_through(self, api):
        result = api(
            "return (await api.list(api.API.products.list, 'products')).length;",
            WHOLE_LIST,
        )

        assert result == {"value": 14}

    def test_asking_for_a_page_opts_out(self, api):
        """The storefront grid pages through nine at a time on purpose. A caller
        that names a page knows it is getting one."""
        result = api(
            "return (await api.request('/api/products/', "
            "{ params: { page: 2, limit: 9 } })).products.length;",
            {
                "products": [{"id": n} for n in range(9)],
                "pagination": {"total": 40, "page": 2, "limit": 9, "pages": 5},
            },
        )

        assert result == {"value": 9}

    def test_a_count_probe_opts_out(self, api):
        """The home page's stat cards read `pagination.total` and never look at
        the records, so one record out of fourteen is what they meant to ask
        for."""
        result = api(
            "return (await api.request('/api/products/', "
            "{ params: { limit: 1 }, partial: true })).pagination.total;",
            {
                "products": [{"id": 1}],
                "pagination": {"total": 14, "page": 1, "limit": 1, "pages": 14},
            },
        )

        assert result == {"value": 14}

    def test_a_reply_with_no_envelope_is_left_alone(self, api):
        """Single records, contacts, deletes — most of the API is not a list."""
        result = api(
            "return (await api.request('/api/products/1')).name;",
            {"id": 1, "name": "Caixa Redonda"},
        )

        assert result == {"value": "Caixa Redonda"}


class TestTheCeilingIsWhereWeThinkItIs:
    """The client-side limit and the server's cap have to be the same number, or
    the guard above never fires and the truncation is silent again."""

    def test_the_default_limit_matches_the_api_cap(self):
        from api.pagination import MAX_LIMIT

        source = (
            __import__("pathlib").Path(__file__).parent.parent
            / "static/js/core/api.js"
        ).read_text()

        assert f"limit = {MAX_LIMIT}" in source, (
            f"core/api.js asks for a page size other than MAX_LIMIT={MAX_LIMIT}; "
            "if the two drift, a truncated list stops being detectable"
        )
