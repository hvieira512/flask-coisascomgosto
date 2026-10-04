<?php

use App\Http\Controllers\Controller;

/*
 * static/js/core/api.js, imported from the running app and driven with
 * window.fetch replaced, so these are the shipped functions answering an
 * envelope of our choosing.
 *
 * What is pinned down is the ceiling. The API caps `limit` at 100, so list()
 * walks every page, and a bare request for a list that comes back short fails
 * instead of quietly rendering part of it.
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

    it('is not swallowed by requestOr either', function () {
        expect(apiLayerRun("return await api.requestOr('/api/products/', { products: [] });", $this->overTheCeiling))
            ->toHaveKey('error');
    });
});

// Page n answers ids 100(n-1)..; 250 records come back as three pages.
it('gathers every page into list', function () {
    $result = apiLayerRun(<<<'JS'
        window.fetch = async (url) => {
            const page = Number(new URL(url).searchParams.get("page"));
            const count = page < 3 ? 100 : 50;
            return new Response(JSON.stringify({
                products: Array.from({ length: count }, (_, i) => ({ id: (page - 1) * 100 + i })),
                pagination: { total: 250, page, limit: 100, pages: 3 },
            }));
        };
        const ids = (await api.list(api.API.products.list, 'products')).map((p) => p.id);
        return [ids.length, new Set(ids).size, ids.at(-1)];
        JS, []);

    expect($result)->toBe(['value' => [250, 250, 249]]);
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
    $source = file_get_contents(base_path('public/static/js/core/api.js'));

    expect($source)->toContain('limit = '.Controller::MAX_LIMIT);
});
