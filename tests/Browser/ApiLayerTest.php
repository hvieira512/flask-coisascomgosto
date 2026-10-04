<?php

use App\Http\Controllers\Controller;

/*
 * static/js/core/api.js, imported from the running app and driven with
 * window.fetch replaced, so these are the shipped functions answering an
 * envelope of our choosing.
 *
 * What is pinned down is the ceiling. Every dashboard screen works out its
 * counts from a list it believes is complete, and the API caps `limit` at 100:
 * at 101 products those numbers quietly shrink. These tests make that arrive as
 * a failure instead.
 */

function apiLayerEnvelope(int $count, int $total, int $page = 1, int $limit = 100): array
{
    return [
        'products' => array_map(fn ($n) => ['id' => $n], range(0, $count - 1)),
        'pagination' => ['total' => $total, 'page' => $page, 'limit' => $limit, 'pages' => (int) ceil($total / $limit)],
    ];
}

/**
 * Answer every fetch with $envelope, then run $script as the body of an async
 * function with `api` in scope. Returns its value or the message of what it
 * threw — a thrown Error does not survive the trip out of the browser.
 */
function apiLayerRun(string $script, array $envelope): array
{
    // /auth is the page that needs no session.
    $page = visit('/auth');

    return $page->script(sprintf(<<<'JS'
        async () => {
            const envelope = %s;
            window.fetch = async () => new Response(JSON.stringify(envelope), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            });
            const api = await import("/static/js/core/api.js");
            try {
                return { value: await new Function("api", `return (async () => { ${%s} })()`)(api) };
            } catch (error) {
                return { error: error.message, truncated: error.truncated === true };
            }
        }
        JS, json_encode($envelope), json_encode($script)));
}

describe('a truncated list is refused', function () {
    // 101 records answered 100 at a time: one over the API's own ceiling.
    beforeEach(fn () => $this->overTheCeiling = apiLayerEnvelope(100, 101));

    it('throws from request, naming the endpoint and the numbers', function () {
        $result = apiLayerRun("return await api.request('/api/products/');", $this->overTheCeiling);

        expect($result)->toHaveKey('error')
            ->and($result['error'])->toContain('/api/products/')->toContain('100')->toContain('101');
    });

    // "truncated" alone leaves the next reader guessing at the fix.
    it('says what to do about it', function () {
        $result = apiLayerRun("return await api.request('/api/products/');", $this->overTheCeiling);

        expect($result['error'])->toContain('pagination');
    });

    it('throws from list too', function () {
        expect(apiLayerRun("return await api.list(api.API.products.list, 'products');", $this->overTheCeiling))
            ->toHaveKey('error');
    });

    // orEmpty is for a lookup that failed to arrive. A truncated list is a wrong
    // answer, not a missing one, and swallowing it is what kept this invisible.
    it('is not swallowed by orEmpty', function () {
        $result = apiLayerRun("return await api.list(api.API.products.list, 'products', { orEmpty: true });", $this->overTheCeiling);

        expect($result)->toHaveKey('error')
            ->and($result['truncated'])->toBeTrue();
    });

    it('is not swallowed by requestOr either', function () {
        expect(apiLayerRun("return await api.requestOr('/api/products/', { products: [] });", $this->overTheCeiling))
            ->toHaveKey('error');
    });
});

describe('what must keep working', function () {
    it('passes a complete list through', function () {
        expect(apiLayerRun("return (await api.list(api.API.products.list, 'products')).length;", apiLayerEnvelope(14, 14)))
            ->toBe(['value' => 14]);
    });

    // The storefront grid pages nine at a time on purpose.
    it('lets a caller that asks for a page opt out', function () {
        $result = apiLayerRun(
            "return (await api.request('/api/products/', { params: { page: 2, limit: 9 } })).products.length;",
            apiLayerEnvelope(9, 40, 2, 9),
        );

        expect($result)->toBe(['value' => 9]);
    });

    it('lets a count probe opt out', function () {
        $result = apiLayerRun(
            "return (await api.request('/api/products/', { params: { limit: 1 }, partial: true })).pagination.total;",
            apiLayerEnvelope(1, 14, 1, 1),
        );

        expect($result)->toBe(['value' => 14]);
    });

    // Single records, contacts, deletes: most of the API is not a list.
    it('leaves a reply with no envelope alone', function () {
        expect(apiLayerRun("return (await api.request('/api/products/1')).name;", ['id' => 1, 'name' => 'Caixa Redonda']))
            ->toBe(['value' => 'Caixa Redonda']);
    });
});

// If the client's page size and the server's cap drift, the guard above never
// fires and the truncation is silent again.
it('asks for a page the size of the API cap', function () {
    $source = file_get_contents(base_path('static/js/core/api.js'));

    expect($source)->toContain('limit = '.Controller::MAX_LIMIT);
});
