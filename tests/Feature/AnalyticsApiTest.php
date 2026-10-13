<?php

/*
 * GET /api/analytics/overview. The window arithmetic is the part worth testing:
 * everything on the page is "this period against the one before it", and an
 * off-by-one at either boundary would show the owners a rise that was a fall.
 * Events are inserted with explicit timestamps so a test can put one nine days ago.
 */

use Illuminate\Support\Facades\DB;

const ANALYTICS_URL = '/api/analytics/overview';

function analyticsPiece(): array
{
    $product = makeProduct('Caixa Redonda');
    $colorSet = makeColorSet('Preto e Dourado', [makeColor('Preto')['id']]);

    return ['product' => $product, 'variant' => makeVariant($product, $colorSet), 'color_set' => $colorSet];
}

function analyticsRecord(string $kind, int $daysAgo = 0, array $fields = []): void
{
    DB::table('storefront_events')->insert(['kind' => $kind, 'created_at' => DB::raw("NOW() - INTERVAL {$daysAgo} DAY")] + $fields);
}

describe('who may read it', function () {
    it('refuses a stranger', function () {
        $this->getJson(ANALYTICS_URL)->assertUnauthorized();
    });

    it('answers the owners', function () {
        signIn();

        $this->getJson(ANALYTICS_URL)->assertOk();
    });
});

describe('the window', function () {
    beforeEach(fn () => signIn());

    it('defaults to a week', function () {
        expect($this->getJson(ANALYTICS_URL)->json('window.days'))->toBe(7);
    });

    it('takes the days asked for', function () {
        expect($this->getJson(ANALYTICS_URL.'?days=30')->json('window.days'))->toBe(30);
    });

    // A hand-typed ?days=14 is a reasonable question, and 0 or 9999 still has
    // to mean something.
    it('is clamped rather than refused', function (int $asked, int $expected) {
        $this->getJson(ANALYTICS_URL."?days={$asked}")->assertOk()->assertJsonPath('window.days', $expected);
    })->with([[0, 1], [-5, 1], [9999, 365]]);

    it('falls back to the default on nonsense', function () {
        expect($this->getJson(ANALYTICS_URL.'?days=abc')->json('window.days'))->toBe(7);
    });

    it('does not count events outside it', function () {
        $id = analyticsPiece()['product']['id'];
        analyticsRecord('view', 0, ['product_id' => $id]);
        analyticsRecord('view', 9, ['product_id' => $id]);

        expect($this->getJson(ANALYTICS_URL.'?days=7')->json('totals.views'))->toBe(1);
    });

    it('compares against the window before it', function () {
        $id = analyticsPiece()['product']['id'];
        foreach ([1, 9, 10] as $daysAgo) {
            analyticsRecord('view', $daysAgo, ['product_id' => $id]);
        }

        $body = $this->getJson(ANALYTICS_URL.'?days=7')->json();

        expect($body['totals']['views'])->toBe(1)->and($body['previous']['views'])->toBe(2);
    });

    // An event counted in both would show as a rise and a fall at once.
    it('does not overlap the previous window', function () {
        $id = analyticsPiece()['product']['id'];
        foreach (range(0, 13) as $daysAgo) {
            analyticsRecord('view', $daysAgo, ['product_id' => $id]);
        }

        $body = $this->getJson(ANALYTICS_URL.'?days=7')->json();

        expect($body['totals']['views'] + $body['previous']['views'])->toBe(14);
    });

    // A quiet week and a week before recording began are different things.
    it('says counting began at the first event ever, not the window', function () {
        analyticsRecord('view', 200, ['product_id' => analyticsPiece()['product']['id']]);

        $body = $this->getJson(ANALYTICS_URL.'?days=7')->json();

        expect($body['totals']['views'])->toBe(0)->and($body['window']['counting_since'])->not->toBeNull();
    });

    it('says counting has not begun before anything is recorded', function () {
        expect($this->getJson(ANALYTICS_URL)->json('window.counting_since'))->toBeNull();
    });
});

describe('the totals', function () {
    beforeEach(fn () => signIn());

    it('counts each kind separately', function () {
        $id = analyticsPiece()['product']['id'];
        analyticsRecord('visit');
        analyticsRecord('view', 0, ['product_id' => $id]);
        analyticsRecord('view', 0, ['product_id' => $id]);
        analyticsRecord('enquiry', 0, ['product_id' => $id]);
        analyticsRecord('search', 0, ['term' => 'caixa', 'results' => 3]);
        analyticsRecord('filter', 0, ['facet' => 'Tipo', 'facet_label' => 'Caixa']);

        $totals = $this->getJson(ANALYTICS_URL)->json('totals');

        expect($totals['visits'])->toBe(1)
            ->and($totals['views'])->toBe(2)
            ->and($totals['enquiries'])->toBe(1)
            ->and($totals['searches'])->toBe(1);
    });

    it('counts visits, the denominator for everything else', function () {
        foreach (range(1, 5) as $_) {
            analyticsRecord('visit');
        }
        analyticsRecord('view', 0, ['product_id' => analyticsPiece()['product']['id']]);

        $totals = $this->getJson(ANALYTICS_URL)->json('totals');

        expect($totals['visits'])->toBe(5)->and($totals['views'])->toBe(1);
    });

    it('counts distinct pieces, not views', function () {
        $id = analyticsPiece()['product']['id'];
        $other = makeProduct('Moldura Oval');
        analyticsRecord('view', 0, ['product_id' => $id]);
        analyticsRecord('view', 0, ['product_id' => $id]);
        analyticsRecord('view', 0, ['product_id' => $other['id']]);

        $totals = $this->getJson(ANALYTICS_URL)->json('totals');

        expect($totals['views'])->toBe(3)->and($totals['pieces'])->toBe(2);
    });

    // SUM() over no rows is NULL, and the page has to print a number.
    it('answers zeros, not nulls, for an empty window', function () {
        expect($this->getJson(ANALYTICS_URL)->json('totals'))
            ->toBe(['visits' => 0, 'views' => 0, 'pieces' => 0, 'enquiries' => 0, 'searches' => 0]);
    });
});

describe('the daily series', function () {
    beforeEach(fn () => signIn());

    it('has one value per day in the window', function () {
        analyticsRecord('view', 0, ['product_id' => analyticsPiece()['product']['id']]);

        $daily = $this->getJson(ANALYTICS_URL.'?days=30')->json('daily');

        foreach (['visits', 'views', 'pieces', 'enquiries', 'searches'] as $key) {
            expect($daily[$key])->toHaveCount(30);
        }
    });

    // SQL only returns days that have rows; a line drawn straight across a
    // silent week claims the week was busy.
    it('fills silent days with zeros and ends on today', function () {
        $id = analyticsPiece()['product']['id'];
        analyticsRecord('view', 0, ['product_id' => $id]);
        analyticsRecord('view', 0, ['product_id' => $id]);

        expect($this->getJson(ANALYTICS_URL.'?days=7')->json('daily.views'))->toBe([0, 0, 0, 0, 0, 0, 2]);
    });

    it('puts an older day in its own place', function () {
        analyticsRecord('view', 3, ['product_id' => analyticsPiece()['product']['id']]);

        expect($this->getJson(ANALYTICS_URL.'?days=7')->json('daily.views'))->toBe([0, 0, 0, 1, 0, 0, 0]);
    });

    it('adds up to the total', function () {
        $id = analyticsPiece()['product']['id'];
        foreach ([0, 1, 1, 5] as $daysAgo) {
            analyticsRecord('view', $daysAgo, ['product_id' => $id]);
        }

        $body = $this->getJson(ANALYTICS_URL.'?days=7')->json();

        expect(array_sum($body['daily']['views']))->toBe(4)->and($body['totals']['views'])->toBe(4);
    });

    it('is a row of zeros when nothing is recorded', function () {
        expect($this->getJson(ANALYTICS_URL.'?days=7')->json('daily.views'))->toBe(array_fill(0, 7, 0));
    });
});

describe('the most viewed', function () {
    beforeEach(fn () => signIn());

    it('carries the name and both counts', function () {
        $id = analyticsPiece()['product']['id'];
        analyticsRecord('view', 0, ['product_id' => $id]);
        analyticsRecord('enquiry', 0, ['product_id' => $id]);

        $rows = $this->getJson(ANALYTICS_URL)->json('top_products');

        expect($rows)->toHaveCount(1)
            ->and($rows[0]['name'])->toBe('Caixa Redonda')
            ->and([$rows[0]['views'], $rows[0]['enquiries']])->toBe([1, 1]);
    });

    it('is ordered by views', function () {
        $id = analyticsPiece()['product']['id'];
        $quiet = makeProduct('Moldura Oval');
        analyticsRecord('view', 0, ['product_id' => $quiet['id']]);
        foreach (range(1, 3) as $_) {
            analyticsRecord('view', 0, ['product_id' => $id]);
        }

        expect($this->getJson(ANALYTICS_URL)->json('top_products.*.name'))->toBe(['Caixa Redonda', 'Moldura Oval']);
    });

    // An enquiry from a shared link: zero views and a question is worth seeing.
    it('keeps a piece asked about but never opened', function () {
        analyticsRecord('enquiry', 0, ['product_id' => analyticsPiece()['product']['id']]);

        $rows = $this->getJson(ANALYTICS_URL)->json('top_products');

        expect($rows)->toHaveCount(1)->and([$rows[0]['views'], $rows[0]['enquiries']])->toBe([0, 1]);
    });
});

describe('what people ask for', function () {
    beforeEach(fn () => signIn());

    it('groups enquiries by colour', function () {
        $piece = analyticsPiece();
        foreach (range(1, 2) as $_) {
            analyticsRecord('enquiry', 0, ['product_id' => $piece['product']['id'], 'variant_id' => $piece['variant']['id']]);
        }

        $rows = $this->getJson(ANALYTICS_URL)->json('top_color_sets');

        expect($rows)->toHaveCount(1)
            ->and($rows[0]['name'])->toBe('Preto e Dourado')
            ->and($rows[0]['enquiries'])->toBe(2);
    });

    it('does not count an enquiry with no colour as a colour anybody asked for', function () {
        analyticsRecord('enquiry', 0, ['product_id' => analyticsPiece()['product']['id']]);

        expect($this->getJson(ANALYTICS_URL)->json('top_color_sets'))->toBe([]);
    });
});

// Hugo does not want to read what people searched for, so the overview never
// answers it; the terms are still recorded and counted.
describe('searches', function () {
    beforeEach(fn () => signIn());

    it('leaves the words out of the answer', function () {
        analyticsRecord('search', 0, ['term' => 'tabuleiro de queijos', 'results' => 0]);

        $response = $this->getJson(ANALYTICS_URL);

        expect($response->json())->not->toHaveKey('empty_searches')
            ->and($response->getContent())->not->toContain('tabuleiro');
    });

    it('still counts them', function () {
        analyticsRecord('search', 0, ['term' => 'tabuleiro de queijos', 'results' => 0]);

        expect($this->getJson(ANALYTICS_URL)->json('totals.searches'))->toBe(1);
    });
});

describe('the filters used', function () {
    beforeEach(fn () => signIn());

    it('groups them by facet and label', function () {
        analyticsRecord('filter', 0, ['facet' => 'Tipo', 'facet_label' => 'Caixa']);
        analyticsRecord('filter', 0, ['facet' => 'Tipo', 'facet_label' => 'Caixa']);
        analyticsRecord('filter', 0, ['facet' => 'Colecção', 'facet_label' => 'Filigrana']);

        $rows = $this->getJson(ANALYTICS_URL)->json('top_filters');

        expect($rows[0])->toBe(['facet' => 'Tipo', 'label' => 'Caixa', 'count' => 2])
            ->and($rows)->toContain(['facet' => 'Colecção', 'label' => 'Filigrana', 'count' => 1]);
    });
});

describe('the catalogue line', function () {
    beforeEach(fn () => signIn());

    it('rides along so the page costs one request', function () {
        analyticsPiece();

        $catalogue = $this->getJson(ANALYTICS_URL)->json('catalogue');

        expect($catalogue['products'])->toBe(1)
            ->and($catalogue['color_sets'])->toBe(1)
            ->and($catalogue['colors'])->toBeGreaterThanOrEqual(1)
            ->and($catalogue['collections'])->toBe(0);
    });

    // Every window reaches back before the only piece was dated, so the answer
    // is "cannot say" rather than "one new piece".
    it('leaves pieces added out until the dates mean something', function () {
        analyticsPiece();

        expect($this->getJson(ANALYTICS_URL)->json('catalogue.added'))->toBeNull();
    });
});
