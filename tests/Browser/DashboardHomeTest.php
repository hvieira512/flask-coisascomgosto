<?php

use Illuminate\Support\Facades\DB;

/*
 * The dashboard's home page answers one question: whether anybody looks at any
 * of this. The tests worth having are about what it says when the numbers are
 * awkward — nothing recorded yet, a quiet week, a first week with nothing to
 * compare against — because those states make a dashboard look broken.
 */

beforeEach(fn () => signIn(makeUser('dash')));

function homeRecord(string $kind, int $daysAgo = 0, array $fields = []): void
{
    DB::table('storefront_events')->insert([
        'kind' => $kind,
        'created_at' => DB::raw('NOW() - INTERVAL '.(int) $daysAgo.' DAY'),
        ...$fields,
    ]);
}

function homePiece(): array
{
    $product = makeProduct('Caixa Redonda');
    $variant = makeVariant($product, makeColorSet('Preto e Dourado', [makeColor('Preto')['id']]));

    return ['product' => $product, 'variant' => $variant];
}

function homeOpen(?int $days = null, int $width = 1280, int $height = 1000)
{
    $page = visit('/dashboard/home'.($days ? "?dias={$days}" : ''))->resize($width, $height);
    $page->page()->waitForSelector('#totals [data-figure] >> nth=0');

    return $page;
}

// Page::waitForURL builds the request but never sends it, so poll here.
function homeWaitUntil($page, string $condition): void
{
    $met = $page->script("new Promise(resolve => { const end = Date.now() + 5000; (function poll() { if ({$condition}) return resolve(true); if (Date.now() > end) return resolve(false); setTimeout(poll, 50); })(); })");
    expect($met)->toBeTrue("timed out waiting for: {$condition}");
}

function homeText($page, string $selector): string
{
    return $page->script('document.querySelector('.json_encode($selector).').innerText');
}

function homeView(array $piece, int $daysAgo = 0): void
{
    homeRecord('view', $daysAgo, ['product_id' => $piece['product']['id']]);
}

describe('what is gone', function () {
    it('no longer lists pieces without photographs', function () {
        $page = homeOpen();

        $page->assertCount('#missing-photos', 0);
        expect($page->content())->not->toContain('sem fotografia');
    });

    it('no longer shows events', function () {
        $page = homeOpen();

        $page->assertCount('#upcoming-events', 0);
        expect($page->content())->not->toContain('Próximos eventos');
    });

    it('makes the four counters one line', function () {
        $page = homeOpen();

        expect(homeText($page, '#catalogue-line'))->toContain('peças')->toContain('colecções');
        $page->assertCount('#stat-cards', 0);
    });

    it('costs one request', function () {
        $page = homeOpen();
        usleep(400_000);

        $calls = $page->script("performance.getEntriesByType('resource').map(e => e.name).filter(u => u.includes('/api/'))");
        expect($calls)->toHaveCount(1)
            ->and($calls[0])->toContain('analytics/overview');
    });
});

// The first thing the owners will see. Zeros that cannot say why are a page that
// looks broken.
describe('before anything is recorded', function () {
    it('says counting has not started', function () {
        $page = homeOpen();

        expect(homeText($page, '#totals'))->toContain('Ainda não há nada registado');
        $page->assertNoJavaScriptErrors();
    });

    it('says it once rather than in every panel', function () {
        expect(substr_count(homeOpen()->content(), 'Ainda não há nada registado'))->toBe(1);
    });

    it('has no panel pretending to have data', function () {
        $page = homeOpen();

        foreach (['most-viewed', 'asked-colors', 'top-filters'] as $panel) {
            $page->assertCount("#{$panel} li", 0);
        }
    });

    it('leaves the start date out of the catalogue line', function () {
        expect(homeText(homeOpen(), '#catalogue-line'))->not->toContain('a contar desde');
    });

    it('claims no change on any figure', function () {
        expect(homeText(homeOpen(), '#totals'))->not->toContain('vs. período anterior');
    });
});

describe('with something recorded', function () {
    it('shows the window\'s own totals', function () {
        $piece = homePiece();
        homeView($piece);
        homeView($piece, 40);

        $page = homeOpen(7);

        expect(homeText($page, '[data-figure=views] .data'))->toBe('1');
        $page->assertNoJavaScriptErrors();
    });

    it('takes in more with a wider window', function () {
        $piece = homePiece();
        homeView($piece);
        homeView($piece, 40);

        expect(homeText(homeOpen(90), '[data-figure=views] .data'))->toBe('2');
    });

    it('shows a rise against the previous window', function () {
        $piece = homePiece();
        homeView($piece);
        homeView($piece);
        homeView($piece, 9);

        expect(homeText(homeOpen(7), '#totals'))->toContain('▲ 1 vs. período anterior');
    });

    it('shows a fall too', function () {
        $piece = homePiece();
        homeView($piece);
        foreach (range(1, 4) as $_) {
            homeView($piece, 9);
        }

        expect(homeText(homeOpen(7), '#totals'))->toContain('▼ 3 vs. período anterior');
    });

    it('lists the most viewed piece with both counts', function () {
        $piece = homePiece();
        homeView($piece);
        homeRecord('enquiry', fields: ['product_id' => $piece['product']['id']]);

        expect(homeText(homeOpen(), '#most-viewed li'))->toContain('Caixa Redonda')->toContain('1 pedido');
    });

    // Openings without a single request is a different problem from nobody
    // opening it; the two columns side by side make it visible.
    it('says so for a piece nobody asked about', function () {
        homeView(homePiece());

        expect(homeText(homeOpen(), '#most-viewed li'))->toContain('sem pedidos');
    });

    it('links the piece to it in the catalogue', function () {
        homeView(homePiece());
        $page = homeOpen();

        $page->click('#most-viewed a');

        // The name is percent-encoded, so assert on what the products page made
        // of it rather than on the query string.
        $page->page()->waitForSelector('#product-list tr[data-product-id] >> nth=0');
        homeWaitUntil($page, "location.pathname === '/dashboard/products' && location.search.startsWith('?q=')");
        expect($page->value('#filter-q'))->toBe('Caixa Redonda');
    });

    it('names the colour asked for', function () {
        $piece = homePiece();
        homeRecord('enquiry', fields: ['product_id' => $piece['product']['id'], 'variant_id' => $piece['variant']['id']]);

        expect(homeText(homeOpen(), '#asked-colors'))->toContain('Preto e Dourado');
    });

    // The page shows how many searches there were and never what they said.
    it('counts a search without quoting it', function () {
        homeRecord('search', fields: ['term' => 'tabuleiro de queijos', 'results' => 0]);
        $page = homeOpen();

        // The eyebrow labels are uppercased in CSS.
        expect(mb_strtolower(homeText($page, '#totals')))->toContain('procuras')
            ->and($page->content())->not->toContain('tabuleiro');
    });

    it('shows the filter group and the option', function () {
        homeRecord('filter', fields: ['facet' => 'Tipo', 'facet_label' => 'Caixa']);

        expect(homeText(homeOpen(), '#top-filters'))->toContain('Tipo')->toContain('Caixa');
    });

    // Recording has started, so an empty panel is a fact about the period.
    it('says a quiet period is quiet rather than showing a dash', function () {
        homeView(homePiece());

        expect(homeText(homeOpen(), '#asked-colors'))->toContain('Ninguém perguntou por uma cor');
    });
});

// Hugo could not tell what the page was telling him: "O que são as perguntas? O
// que são Vistas?" The labels are the answer, and so is the sentence under them.
describe('the figures say what they count', function () {
    it('shows every figure, named', function () {
        homeRecord('visit');
        homeView(homePiece());

        $labels = homeOpen()->script("[...document.querySelectorAll('#totals [data-figure]')].map(e => e.innerText)");

        expect($labels)->toHaveCount(5);
        $joined = mb_strtolower(implode(' ', $labels));
        foreach (['visitas', 'aberturas de peças', 'peças diferentes', 'pedidos de informação', 'procuras'] as $word) {
            expect($joined)->toContain($word);
        }
    });

    it('explains an opening and a request', function () {
        homeView(homePiece());

        expect(homeText(homeOpen(), '#totals > .help'))->toContain('abrir a loja')->toContain('Pedir informações');
    });

    it('tells a visit from an opening', function () {
        foreach (range(1, 3) as $_) {
            homeRecord('visit');
        }
        homeView(homePiece());

        $page = homeOpen();

        expect(homeText($page, '[data-figure=visits] .data'))->toBe('3')
            ->and(homeText($page, '[data-figure=views] .data'))->toBe('1');
    });
});

// A line is only worth drawing when there is a shape to see; a flat rule would
// read as "we measured this and it was nothing".
describe('the sparklines', function () {
    it('draws a line for a figure with data', function () {
        $piece = homePiece();
        homeView($piece, 2);
        homeView($piece);

        $page = homeOpen();

        expect($page->script("document.querySelectorAll('#totals svg polyline').length"))->toBeGreaterThanOrEqual(1);
        $page->assertNoJavaScriptErrors();
    });

    it('draws nothing when nothing is recorded', function () {
        homeOpen()->assertCount('#totals svg', 0);
    });

    it('draws nothing for a figure that stayed at zero', function () {
        homeView(homePiece());

        homeOpen()
            ->assertCount('[data-figure=searches] svg', 0)
            ->assertCount('[data-figure=views] svg', 1);
    });

    it('has one point per day of the window', function () {
        homeView(homePiece());

        $points = homeOpen(30)->script("document.querySelector('#totals svg polyline').getAttribute('points')");

        expect(preg_split('/\s+/', trim($points)))->toHaveCount(30);
    });
});

// Pieces dated before created_at existed all carry the column's arrival date.
// Until a window begins after the earliest of them the phrase is left out, rather
// than reporting that backfill as this week's work.
describe('what is new in the catalogue', function () {
    it('says nothing while it cannot be said', function () {
        homePiece();

        expect(homeText(homeOpen(), '#catalogue-line'))->not->toContain('nova');
    });

    it('counts a new piece once the dates are real', function () {
        $old = makeProduct('Peça antiga');
        DB::table('products')->where('id', $old['id'])->update(['created_at' => DB::raw('NOW() - INTERVAL 60 DAY')]);
        homePiece();

        expect(homeText(homeOpen(7), '#catalogue-line'))->toContain('1 nova');
    });
});

describe('the window selector', function () {
    it('opens on a week', function () {
        expect(homeText(homeOpen(), '[data-days][aria-pressed=true]'))->toBe('7 dias');
    });

    it('puts the choice in the url', function () {
        $page = homeOpen();

        $page->click("[data-days='30']");

        homeWaitUntil($page, "location.href.endsWith('dias=30')");
        expect(homeText($page, '[data-days][aria-pressed=true]'))->toBe('30 dias');
    });

    it('keeps it through a reload', function () {
        $page = homeOpen(90);

        $page->refresh();
        $page->page()->waitForSelector('#totals [data-figure] >> nth=0');

        expect(homeText($page, '[data-days][aria-pressed=true]'))->toBe('90 dias');
    });

    it('says which period in the heading', function () {
        expect(mb_strtolower(homeText(homeOpen(30), '#totals > .eyebrow')))->toContain('neste mês');
    });

    it('falls back to a week for an invented window', function () {
        expect(homeText(homeOpen(999), '[data-days][aria-pressed=true]'))->toBe('7 dias');
    });
});

it('does not scroll sideways on a phone', function () {
    $page = homeOpen(width: 390, height: 780);

    $page->script('window.scrollTo(300, 0)');

    expect($page->script('window.scrollX'))->toBe(0);
});
