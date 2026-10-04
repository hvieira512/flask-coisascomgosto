<?php

/*
 * The collection rail on the catalogue. People ask for the work by collection,
 * so the collections are offered first, as photographs — but it is a rail and
 * not a gate: the grid underneath is already full.
 *
 * Every test visits in its own body: a visit() from beforeEach runs before the
 * browser plugin has connected.
 */

beforeEach(fn () => signIn());

/** The grid is refetched a fetch after anything changes, so wait on what it shows. */
function railWaitUntil($page, string $js): void
{
    for ($i = 0; $i < 100; $i++) {
        if ($page->script($js)) {
            return;
        }
        $page->wait(0.05);
    }
    expect($page->script($js))->toBeTrue("timed out waiting for: {$js}");
}

function railWaitForGrid($page, int $count): void
{
    railWaitUntil($page, "document.querySelectorAll('#product-grid > *').length === {$count}");
}

/** The rail and the grid are two fetches; waiting on the rail alone counted the grid early. */
function railOpen(int $width = 1280, int $height = 900, ?int $pieces = 4)
{
    $page = visit('/products')->resize($width, $height);
    railWaitUntil($page, "document.querySelector('#collection-strip .collection-card') !== null");
    if ($pieces !== null) {
        railWaitForGrid($page, $pieces);
    }

    return $page;
}

function railCard(string $name): string
{
    return ".collection-card:has-text(\"{$name}\") >> nth=0";
}

function railShown($page): int
{
    return $page->script("document.querySelectorAll('#product-grid > *').length");
}

function railNothingChosen($page): bool
{
    return $page->script("document.querySelectorAll('.collection-card[aria-pressed=\"true\"]').length === 0");
}

function railNames($page): array
{
    return $page->script("[...document.querySelectorAll('.collection-card-name')].map(e => e.textContent)");
}

function railBox($page, string $selector): array
{
    return $page->script("(() => { const b = document.querySelector('{$selector}').getBoundingClientRect(); return {x: b.x, y: b.y, width: b.width, height: b.height}; })()");
}

/** One rounded side of every element matching $selector. */
function railEdges($page, string $selector, string $side): array
{
    return $page->script("[...document.querySelectorAll('{$selector}')].map(el => Math.round(el.getBoundingClientRect().{$side}))");
}

/** Three collections, one with nothing behind it, and a piece belonging to none — the case a gate would hide. */
function railSeed(): array
{
    $filigrana = makeCollection('Filigrana');
    $bordados = makeCollection('Bordados');
    makeCollection('Vazia');

    putInCollection(makeProduct('Caixa Redonda'), $filigrana);
    putInCollection(makeProduct('Caixa Quadrada'), $filigrana);
    putInCollection(makeProduct('Bastidor'), $bordados);
    makeProduct('Peça sem colecção');

    return ['filigrana' => $filigrana, 'bordados' => $bordados];
}

function railFiltered()
{
    $page = railOpen();
    $page->click(railCard('Filigrana'));
    railWaitUntil($page, "document.querySelector('#active-filters .filter-badge') !== null");

    return $page;
}

describe('the rail', function () {
    beforeEach(function () {
        $this->ids = railSeed();
    });

    it('offers every collection, with no "Ver tudo" tile', function () {
        $page = railOpen();

        // Choosing the chosen one again is how you get back to everything.
        expect(railNames($page))->not->toContain('Ver tudo')
            ->toContain('Filigrana', 'Bordados')
            // Shown even with nothing filed under it: the empty ones were the ones with covers.
            ->toContain('Vazia');
        $page->assertNoJavaScriptErrors();
    });

    it('shows a collection with no pieces but does not offer it', function () {
        $page = railOpen();
        $empty = railCard('Vazia');
        $find = "[...document.querySelectorAll('.collection-card')].find(el => el.textContent.includes('Vazia'))";

        $page->assertAttribute($empty, 'aria-disabled', 'true')
            ->assertAttributeMissing($empty, 'data-collection-id');
        expect(mb_strtolower($page->script("{$find}.innerText")))->toContain('ainda sem peças');

        // Playwright refuses to click an aria-disabled button, so the click is dispatched directly.
        $page->script("{$find}.click()");
        $page->wait(0.3);

        expect(railNothingChosen($page))->toBeTrue('an empty collection must not filter anything')
            ->and(railShown($page))->toBe(4);
    });

    it('fills the grid before anything is chosen', function () {
        $page = railOpen();

        expect(railNothingChosen($page))->toBeTrue()
            ->and(railShown($page))->toBe(4);
        $page->assertVisible('#product-grid');
    });

    it('reaches the piece that belongs to no collection', function () {
        railOpen()->assertSeeIn('#product-grid', 'Peça sem colecção');
    });

    it('filters the grid when one is chosen', function () {
        $page = railOpen();
        $page->click(railCard('Filigrana'));
        railWaitForGrid($page, 2);

        $page->assertAttribute(railCard('Filigrana'), 'aria-pressed', 'true');
        expect(railNothingChosen($page))->toBeFalse();
    });

    // The cards are the only way to choose a collection; a checkbox list beside them asked twice.
    it('is not repeated in the sidebar', function () {
        $page = railOpen();

        $page->assertCount('[data-facet="collections"]', 0);
        expect($page->script("[...document.querySelectorAll('#filter-groups .filter-group-label')].map(e => e.textContent.trim())"))
            ->toBe(['Tipo', 'Material']);
    });

    it('drives the ordinary filter state: the URL, the badge and Limpar tudo', function () {
        $page = railOpen();
        $page->click(railCard('Filigrana'));
        railWaitUntil($page, "location.search.includes('collection_id')");

        expect($page->url())->toContain("collection_id={$this->ids['filigrana']['id']}");
        $page->assertSeeIn('#active-filters', 'Filigrana');

        $page->click('#clear-filters');
        // The grid, not the URL: the URL is rewritten before the products are fetched.
        railWaitForGrid($page, 4);
        expect(railNothingChosen($page))->toBeTrue();
    });

    // The sidebar's checkboxes add up; a wall of covers reads as "pick one".
    it('replaces the choice rather than adding to it', function () {
        $page = railOpen();
        $page->click(railCard('Filigrana'));
        railWaitUntil($page, "location.search.includes('collection_id')");
        $page->click(railCard('Bordados'));
        railWaitForGrid($page, 1);

        expect(substr_count($page->url(), 'collection_id'))->toBe(1);
        $page->assertAttribute(railCard('Filigrana'), 'aria-pressed', 'false');
    });

    it('goes back to everything when the chosen one is chosen again', function () {
        $page = railOpen();
        $page->click(railCard('Filigrana'));
        railWaitForGrid($page, 2);
        $page->click(railCard('Filigrana'));
        railWaitForGrid($page, 4);

        expect($page->url())->not->toEndWith('collection_id=1')
            ->and(railNothingChosen($page))->toBeTrue();
    });

    // The no-photograph tile carries its own aspect-ratio, so the frame has to decide the shape.
    it('draws every card the same shape', function () {
        $page = railOpen();

        expect(array_unique(railEdges($page, '.collection-cover', 'height')))->toHaveCount(1)
            ->and(array_unique(railEdges($page, '.collection-card-name', 'top')))->toHaveCount(1);
    });

    // Grow with a ceiling: three collections sharing the row came out 367px each. A tile is 13-16rem.
    it('keeps a tile the same size whatever the count', function () {
        $widths = railEdges(railOpen(), '.collection-card', 'width');

        expect(array_unique($widths))->toHaveCount(1)
            ->and($widths[0])->toBeGreaterThanOrEqual(208)->toBeLessThanOrEqual(256);
    });

    /*
     * The ring is an outline rather than a border, so it is painted over the
     * tile instead of adding to its box: marking it must not move anything.
     */
    it('outlines the chosen tile', function () {
        $page = railOpen();
        $page->click(railCard('Filigrana'));
        railWaitForGrid($page, 2);

        $outline = $page->script("(() => { const s = getComputedStyle(document.querySelector('.collection-card[aria-pressed=\"true\"]')); return {width: s.outlineWidth, style: s.outlineStyle}; })()");
        expect($outline)->toBe(['width' => '2px', 'style' => 'solid']);
    });

    it('does not move anything when a tile is chosen', function () {
        $page = railOpen();
        $before = railBox($page, '#collection-strip');

        $page->click(railCard('Filigrana'));
        railWaitForGrid($page, 2);
        $after = railBox($page, '#collection-strip');

        expect(abs($before['height'] - $after['height']))->toBeLessThan(1)
            ->and(abs($before['y'] - $after['y']))->toBeLessThan(1);
    });

    // A badge row of its own pushed the pieces 48px down; a badge taller than the line box, 5px.
    it('does not push the grid down when a filter is chosen', function () {
        $page = railOpen();
        $before = railBox($page, '#product-grid')['y'];

        $page->click(railCard('Filigrana'));
        railWaitForGrid($page, 2);

        expect(round(railBox($page, '#product-grid')['y']))->toBe(round($before));
    });
});

// The applied filters sit on the heading line, beside the count they explain.
describe('the applied filters', function () {
    beforeEach(fn () => railSeed());

    it('sit above the collections, not between them and the grid', function () {
        $page = railFiltered();

        expect(railBox($page, '#active-filters')['y'])->toBeLessThan(railBox($page, '#collection-rail')['y']);
    });

    it('sit next to the count', function () {
        $page = railFiltered();
        $badge = railBox($page, '.filter-badge');
        $gap = railBox($page, '#result-count')['x'] - ($badge['x'] + $badge['width']);

        expect($gap)->toBeGreaterThanOrEqual(0)->toBeLessThan(24, 'the badge drifted away from the number it explains');
    });

    // Fitting the line must not shrink it below a tap target; the whole badge removes the filter.
    it('are still big enough to hit', function () {
        $badge = railBox(railFiltered(), '.filter-badge');

        expect($badge['height'])->toBeGreaterThanOrEqual(24)
            ->and($badge['width'])->toBeGreaterThanOrEqual(24);
    });

    it('remove the filter when the badge is clicked', function () {
        $page = railFiltered();
        $page->click('.filter-badge');
        railWaitForGrid($page, 4);

        $page->assertMissing('#active-filters');
    });
});

describe('on a phone', function () {
    beforeEach(function () {
        foreach (['Filigrana', 'Bordados', 'Lenços'] as $name) {
            putInCollection(makeProduct("Peça {$name}"), makeCollection($name));
        }
    });

    // Four covers cannot fit across 390px; it has to be the rail that scrolls, not the document.
    it('scrolls the rail sideways and not the page', function () {
        $state = railOpen(390, 780, 3)->script(<<<'JS'
            (() => {
                const strip = document.getElementById('collection-strip');
                const style = getComputedStyle(strip);
                return {
                    display: style.display,
                    overflowX: style.overflowX,
                    snap: style.scrollSnapType,
                    railScrolls: strip.scrollWidth > strip.clientWidth,
                    pageScrolls: document.documentElement.scrollWidth > window.innerWidth,
                };
            })()
            JS);

        expect($state['display'])->toBe('flex')
            ->and($state['overflowX'])->toBe('auto')
            ->and($state['snap'])->toContain('x')
            ->and($state['railScrolls'])->toBeTrue()
            ->and($state['pageScrolls'])->toBeFalse('the catalogue must not scroll sideways');
    });

    it('keeps the grid underneath', function () {
        railOpen(390, 780, 3)->assertCount('#product-grid > *', 3);
    });

    // One badge fits beside the title at 390px; two must drop onto their own line rather than crush it.
    it('wraps several filters instead of squeezing the heading', function () {
        $page = railOpen(390, 780, 3);
        $page->click(railCard('Filigrana'));
        railWaitUntil($page, "document.querySelector('#active-filters .filter-badge') !== null");
        $page->click('[data-facet="types"] .filter-entry >> nth=0');
        railWaitUntil($page, "document.querySelectorAll('.filter-badge').length === 2");

        $title = railBox($page, 'h1');
        expect(railBox($page, '#active-filters')['y'])
            ->toBeGreaterThanOrEqual($title['y'] + $title['height'] - 4, "two badges stayed on the title's line and squeezed it")
            ->and($page->script('document.documentElement.scrollWidth > window.innerWidth'))->toBeFalse('the catalogue must not scroll sideways');
    });
});

/*
 * Eight collections rather than three. A wrapping grid went ragged at eight and
 * pushed the pieces off the fold; a scrolling row that grew its own column
 * instead made the whole catalogue scroll sideways.
 */
describe('a crowded rail', function () {
    beforeEach(function () {
        foreach (['Filigrana', 'Bordados', 'Lenços', 'Barra da Saia', 'Coração de Viana', 'Presépios', 'Natal', 'Casamento'] as $name) {
            putInCollection(makeProduct("Peça de {$name}"), makeCollection($name));
        }
    });

    it('stays one row', function () {
        expect(array_unique(railEdges(railOpen(1280, 1000, null), '.collection-card', 'top')))->toHaveCount(1);
    });

    it('scrolls the rail and not the catalogue', function () {
        $state = railOpen(1280, 1000, null)->script(<<<'JS'
            (() => {
                const strip = document.getElementById('collection-strip');
                return {
                    railScrolls: strip.scrollWidth > strip.clientWidth,
                    stripFitsItsColumn: strip.clientWidth <= strip.closest('.container').clientWidth,
                    pageScrolls: document.documentElement.scrollWidth > window.innerWidth,
                };
            })()
            JS);

        expect($state['railScrolls'])->toBeTrue('eight cards must scroll, not squeeze')
            ->and($state['stripFitsItsColumn'])->toBeTrue('the rail grew past its container')
            ->and($state['pageScrolls'])->toBeFalse('the catalogue must not scroll sideways');
    });

    it('keeps the pieces on the fold', function () {
        expect(railBox(railOpen(1280, 1000, null), '#product-grid')['y'])->toBeLessThan(500);
    });

    // "Coração de Viana" wraps where "Natal" does not, so the count is pinned to the card's bottom.
    it('lines the counts up even when a name wraps', function () {
        expect(array_unique(railEdges(railOpen(1280, 1000, null), '.collection-card-detail', 'bottom')))->toHaveCount(1);
    });
});

describe('when there is little to choose', function () {
    // The rail is the only way to filter by collection, so hiding it at one removed the filter.
    it('still draws a rail for a single collection', function () {
        putInCollection(makeProduct('Caixa'), makeCollection('Filigrana'));
        makeProduct('Peça sem colecção');

        expect(railNames(railOpen(pieces: null)))->toBe(['Filigrana']);
    });

    it('hides it when there are no collections at all', function () {
        makeProduct('Caixa');

        $page = visit('/products')->resize(1280, 900);
        railWaitUntil($page, "document.querySelector('#product-grid > *') !== null");

        $page->assertMissing('#collection-rail')
            ->assertCount('#product-grid > *', 1);
    });
});
