<?php

use Illuminate\Support\Facades\DB;

/*
 * What the storefront records. Every rule here is about *when* something
 * counts, which the endpoint cannot decide: one view per piece per tab, an
 * enquiry carrying what was chosen at the click, a search with what it found,
 * and a filter only on the way on.
 */

beforeEach(function () {
    signIn();

    $box = makeProductType('Caixa');
    $frame = makeProductType('Moldura');
    $this->piece = makeProduct('Caixa Redonda', typeId: $box['id']);
    makeProduct('Moldura Oval', typeId: $frame['id']);

    $this->variants = [];
    foreach (['Preto e Dourado', 'Branco e Dourado'] as $name) {
        $this->variants[$name] = makeVariant($this->piece, makeColorSet($name, [makeColor("Cor {$name}")['id']]));
    }

    $this->size = $this->getJson('/api/sizes/')->json('sizes.0');
    $this->putJson("/api/products/{$this->piece['id']}/sizes", ['size_ids' => [$this->size['id']]])->assertOk();
});

function trackingWaitUntil($page, string $js): void
{
    for ($i = 0; $i < 100; $i++) {
        if ($page->script($js)) {
            return;
        }
        $page->wait(0.05);
    }
    expect($page->script($js))->toBeTrue("timed out waiting for: {$js}");
}

/**
 * Wait for the log to hold $expected rows of $kind. The beacons are fire and
 * forget, so there is nothing on the page to wait for. Waiting through the page
 * keeps the in-process server answering them.
 */
function trackingEvents($page, string $kind, int $expected = 1): array
{
    for ($i = 0; $i < 100; $i++) {
        $rows = DB::table('storefront_events')->where('kind', $kind)->orderBy('id')->get()->all();
        if (count($rows) >= $expected) {
            return $rows;
        }
        $page->wait(0.05);
    }
    expect($rows)->toHaveCount($expected, "waited for {$expected} {$kind} event(s)");

    return $rows;
}

function trackingOnly($page, string $kind): object
{
    $rows = trackingEvents($page, $kind);
    expect($rows)->toHaveCount(1);

    return $rows[0];
}

/** A beacon that must not be sent has no signal to wait for, only its absence. */
function trackingNoMoreThan($page, string $kind, int $count): void
{
    $page->wait(0.4);
    expect(DB::table('storefront_events')->where('kind', $kind)->count())->toBe($count);
}

/** Click through to WhatsApp without leaving the page. */
function trackingAsk($page): void
{
    $page->script("(() => { const link = document.getElementById('enquiry-link'); link.removeAttribute('target'); link.setAttribute('href', 'javascript:void 0'); })()");
    $page->click('#enquiry-link');
}

function trackingCatalogue()
{
    $page = visit('/products')->resize(1280, 900);
    trackingWaitUntil($page, "document.querySelector('#product-grid .product-card') !== null");

    return $page;
}

/*
 * The denominator: "Vistas" was expected to mean arrivals at the site, and
 * nothing counted those, so eighteen openings could be eighteen people or one.
 */
describe('a visit', function () {
    it('is counted once on any page of the shop', function (string $path) {
        $page = visit($path)->resize(1280, 900);

        expect(trackingEvents($page, 'visit'))->toHaveCount(1);
        $page->assertNoJavaScriptErrors();
    })->with(['/', '/products', '/products/1']);

    it('stays one visit while walking around the shop', function () {
        $page = visit('/');
        trackingEvents($page, 'visit');

        $page->navigate('/products');
        $page->navigate("/products/{$this->piece['id']}");
        $page->refresh();

        trackingNoMoreThan($page, 'visit', 1);
    });

    // Each visit() is a browser context of its own, which is a new tab.
    it('is counted again in a new tab', function () {
        trackingEvents(visit('/'), 'visit');

        expect(trackingEvents(visit('/'), 'visit', 2))->toHaveCount(2);
    });

    it('says nothing but that somebody arrived', function () {
        $row = trackingOnly(visit('/'), 'visit');

        expect($row->product_id)->toBeNull()
            ->and($row->term)->toBeNull()
            ->and($row->facet)->toBeNull();
    });
});

describe('a view', function () {
    it('is recorded on opening a piece', function () {
        $page = visit("/products/{$this->piece['id']}");

        $row = trackingOnly($page, 'view');
        expect($row->product_id)->toBe($this->piece['id']);
        $page->assertNoJavaScriptErrors();
    });

    // Otherwise the most-viewed list would rank whoever refreshed hardest.
    it('is not recorded again on reload', function () {
        $page = visit("/products/{$this->piece['id']}");
        trackingEvents($page, 'view');

        $page->refresh();
        $page->refresh();

        trackingNoMoreThan($page, 'view', 1);
    });

    it('is recorded for a second piece', function () {
        $page = visit("/products/{$this->piece['id']}");
        trackingEvents($page, 'view');

        $page->navigate('/products/'.($this->piece['id'] + 1));

        expect(trackingEvents($page, 'view', 2))->toHaveCount(2);
    });

    // Per tab: the closest thing to "a visit" without identifying anybody.
    it('counts again in a new tab', function () {
        trackingEvents(visit("/products/{$this->piece['id']}"), 'view');

        expect(trackingEvents(visit("/products/{$this->piece['id']}"), 'view', 2))->toHaveCount(2);
    });

    it('records nothing for a piece that does not exist', function () {
        $page = visit('/products/9999');
        trackingWaitUntil($page, "(() => { const el = document.getElementById('detail-error'); return el && el.getClientRects().length > 0; })()");

        trackingNoMoreThan($page, 'view', 0);
    });
});

describe('an enquiry', function () {
    // The colour says which colourway to make next, not merely that somebody asked.
    it('carries the colour on screen', function () {
        $page = visit("/products/{$this->piece['id']}");
        trackingWaitUntil($page, "document.querySelector('.variant-option') !== null");

        $page->click('.variant-option[title="Branco e Dourado"]');
        trackingAsk($page);

        $row = trackingOnly($page, 'enquiry');
        expect($row->variant_id)->toBe($this->variants['Branco e Dourado']['id']);
        $page->assertNoJavaScriptErrors();
    });

    it('carries the size too', function () {
        $page = visit("/products/{$this->piece['id']}");
        trackingWaitUntil($page, "document.querySelector('#size-options button') !== null");

        $page->click('#size-options button >> nth=0');
        trackingAsk($page);

        $row = trackingOnly($page, 'enquiry');
        expect($row->size_id)->toBe($this->size['id']);
    });

    // Unlike a view: asking again is asking again.
    it('counts twice when asked twice', function () {
        $page = visit("/products/{$this->piece['id']}");
        trackingWaitUntil($page, "document.getElementById('enquiry-link') !== null");

        trackingAsk($page);
        trackingAsk($page);

        expect(trackingEvents($page, 'enquiry', 2))->toHaveCount(2);
    });

    // The tracking rides along with the enquiry; it must not replace what the button is for.
    it('leaves the choice in the WhatsApp message', function () {
        $page = visit("/products/{$this->piece['id']}");
        trackingWaitUntil($page, "document.querySelector('.variant-option') !== null");

        $page->click('.variant-option[title="Branco e Dourado"]');
        $page->click('#size-options button >> nth=0');

        expect(urldecode($page->attribute('#enquiry-link', 'href')))
            ->toContain('Branco e Dourado')
            ->toContain($this->size['name']);
    });
});

describe('a search', function () {
    it('is recorded with what it found', function () {
        $page = trackingCatalogue();

        $page->fill('#filter-search', 'Caixa');

        $row = trackingOnly($page, 'search');
        expect($row->term)->toBe('caixa')
            ->and($row->results)->toBe(1, 'one piece is called Caixa Redonda');
        $page->assertNoJavaScriptErrors();
    });

    // A list of things people want and the catalogue does not offer.
    it('is recorded when it finds nothing', function () {
        $page = trackingCatalogue();

        $page->fill('#filter-search', 'tabuleiro de queijos');

        $row = trackingOnly($page, 'search');
        expect($row->term)->toBe('tabuleiro de queijos')
            ->and($row->results)->toBe(0);
    });

    it('ignores two letters, which are somebody still typing', function () {
        $page = trackingCatalogue();

        $page->fill('#filter-search', 'ca');

        trackingNoMoreThan($page, 'search', 0);
    });

    // The term rides along with every refetch of the grid; only the term itself is a search.
    it('is not recorded again when narrowed by a filter', function () {
        $page = trackingCatalogue();
        $page->fill('#filter-search', 'Caixa');
        trackingEvents($page, 'search');

        $page->click('.filter-entry:has-text("Caixa") >> nth=0');
        trackingEvents($page, 'filter');

        trackingNoMoreThan($page, 'search', 1);
    });
});

describe('a filter', function () {
    it('records the group and the label when ticked', function () {
        $page = visit('/products');
        trackingWaitUntil($page, "document.querySelector('.filter-entry') !== null");

        $page->click('.filter-entry:has-text("Caixa") >> nth=0');

        $row = trackingOnly($page, 'filter');
        expect($row->facet)->toBe('Tipo', "the owners' word, not the API's type_id")
            ->and($row->facet_label)->toBe('Caixa');
        $page->assertNoJavaScriptErrors();
    });

    // Turning a filter off is not a preference, and counting it would double whoever changes their mind.
    it('records nothing when unticked', function () {
        $page = visit('/products');
        trackingWaitUntil($page, "document.querySelector('.filter-entry') !== null");

        $page->click('.filter-entry:has-text("Caixa") >> nth=0');
        trackingEvents($page, 'filter');
        $page->click('.filter-entry:has-text("Caixa") >> nth=0');

        trackingNoMoreThan($page, 'filter', 1);
    });

    // The rail is the only way to filter by collection; the piece gets there through a colourway.
    it('counts choosing a collection from the rail', function () {
        putInCollection($this->piece, makeCollection('Filigrana'));

        $page = visit('/products');
        trackingWaitUntil($page, "document.querySelector('.collection-card') !== null");
        $page->click('.collection-card:has-text("Filigrana") >> nth=0');

        $row = trackingOnly($page, 'filter');
        expect([$row->facet, $row->facet_label])->toBe(['Colecção', 'Filigrana']);
    });
});
