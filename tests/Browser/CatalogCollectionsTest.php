<?php

/*
 * The catalogue opens on its collections and only then on the pieces: one page,
 * the same header and filters, with the grid column swapping between the two
 * and a breadcrumb over the pieces for the way back. The filters never go away
 * and never get lost between the two.
 *
 * Every test visits in its own body: a visit() from beforeEach runs before the
 * browser plugin has connected.
 */

beforeEach(fn () => signIn());

function collectionsWaitUntil($page, string $js): void
{
    for ($i = 0; $i < 100; $i++) {
        if ($page->script($js)) {
            return;
        }
        $page->wait(0.05);
    }
    expect($page->script($js))->toBeTrue("timed out waiting for: {$js}");
}

function collectionsWaitForCards($page, int $count): void
{
    collectionsWaitUntil($page, "document.querySelectorAll('#product-grid .product-card').length === {$count}");
}

/** Two collections with pieces, one without, and a piece filed under none. */
function collectionsSeed(): array
{
    $box = makeProductType('Caixa');
    $frame = makeProductType('Moldura');
    $filigree = makeCollection('Filigrana');
    $embroidery = makeCollection('Bordados');
    makeCollection('Vazia');

    putInCollection(makeProduct('Caixa Redonda', typeId: $box['id']), $filigree);
    putInCollection(makeProduct('Caixa de Joias', typeId: $box['id']), $filigree);
    putInCollection(makeProduct('Bastidor', typeId: $frame['id']), $embroidery);
    makeProduct('Peça sem colecção', typeId: $box['id']);

    return compact('box', 'frame', 'filigree', 'embroidery');
}

function collectionsOpen(string $path = '/products', int $width = 1280, int $height = 900)
{
    $page = visit($path)->resize($width, $height);
    collectionsWaitUntil($page, "document.querySelector('#collection-grid .collection-tile, #product-grid .product-card') !== null");

    return $page;
}

function collectionTile(string $name): string
{
    return ".collection-tile:has-text(\"{$name}\") >> nth=0";
}

function collectionsTileNames($page): array
{
    return $page->script("[...document.querySelectorAll('.collection-tile-name')].map(e => e.textContent.trim())");
}

function collectionsCards($page): int
{
    return $page->script("document.querySelectorAll('#product-grid .product-card').length");
}

function collectionsHidden($page, string $id): bool
{
    return $page->script("document.getElementById('{$id}').hidden");
}

describe('the collections come first', function () {
    beforeEach(function () {
        $this->ids = collectionsSeed();
    });

    it('shows the collections with pieces, and a tile for everything', function () {
        $page = collectionsOpen();

        expect(collectionsTileNames($page))->toBe(['Filigrana', 'Bordados', 'Todas as peças'])
            ->and(collectionsCards($page))->toBe(0)
            ->and(collectionsHidden($page, 'grid-crumbs'))->toBeTrue();
        $page->assertSeeIn('#result-count', '4 peças')->assertNoJavaScriptErrors();
    });

    it('keeps the header and the filters', function () {
        $page = collectionsOpen();

        expect($page->script("document.querySelector('h1').textContent.trim()"))->toBe('Tudo o que fazemos');
        $page->assertVisible('#filter-search')->assertVisible('[data-facet="types"] .filter-entry >> nth=0');
    });

    it('opens a collection in the same column, under a breadcrumb', function () {
        $page = collectionsOpen();
        $page->click(collectionTile('Filigrana'));
        collectionsWaitForCards($page, 2);

        expect($page->url())->toContain("collection_id={$this->ids['filigree']['id']}")
            ->and(collectionsHidden($page, 'collection-grid'))->toBeTrue()
            ->and(collectionsHidden($page, 'grid-crumbs'))->toBeFalse()
            // The page did not change around the grid.
            ->and($page->script("document.querySelector('h1').textContent.trim()"))->toBe('Tudo o que fazemos');
        $page->assertSeeIn('#grid-crumbs', 'Colecções')
            ->assertSeeIn('#grid-crumbs [aria-current="page"]', 'Filigrana')
            ->assertSeeIn('#result-count', '2 peças');
    });

    it('comes back through the breadcrumb', function () {
        $page = collectionsOpen();
        $page->click(collectionTile('Filigrana'));
        collectionsWaitForCards($page, 2);

        $page->click('#grid-crumbs [data-crumb-collections]');
        collectionsWaitUntil($page, "!document.getElementById('collection-grid').hidden && document.querySelectorAll('.collection-tile').length === 3");

        expect($page->url())->not->toContain('collection_id');
    });

    it('comes back with the browser too', function () {
        $page = collectionsOpen();
        $page->click(collectionTile('Filigrana'));
        collectionsWaitForCards($page, 2);

        $page->script('history.back()');
        collectionsWaitUntil($page, "!document.getElementById('collection-grid').hidden && document.querySelectorAll('.collection-tile').length === 3");

        expect($page->url())->not->toContain('collection_id');
    });

    it('reaches the piece that belongs to no collection through "Todas as peças"', function () {
        $page = collectionsOpen();
        $page->click(collectionTile('Todas as peças'));
        collectionsWaitForCards($page, 4);

        expect($page->url())->toContain('all=1');
        $page->assertSeeIn('#product-grid', 'Peça sem colecção')
            ->assertSeeIn('#grid-crumbs [aria-current="page"]', 'Todas as peças');
    });

    it('narrows the collections when a filter is ticked, and carries it inside and back out', function () {
        $page = collectionsOpen();
        $page->click('.filter-entry:has-text("Moldura") >> nth=0');
        collectionsWaitUntil($page, "[...document.querySelectorAll('.collection-tile-name')].map(e => e.textContent.trim()).join() === 'Bordados,Todas as peças'");
        $page->assertSeeIn('#result-count', '1 peça');

        $page->click(collectionTile('Bordados'));
        collectionsWaitForCards($page, 1);
        $page->assertAttribute('.filter-entry:has-text("Moldura") >> nth=0', 'aria-checked', 'true')
            ->assertSeeIn('#active-filters', 'Moldura');

        $page->click('#grid-crumbs [data-crumb-collections]');
        collectionsWaitUntil($page, "!document.getElementById('collection-grid').hidden");
        $page->assertAttribute('.filter-entry:has-text("Moldura") >> nth=0', 'aria-checked', 'true');
    });

    it('scopes the sidebar counts to the open collection', function () {
        $page = collectionsOpen();
        $page->click(collectionTile('Bordados'));
        collectionsWaitForCards($page, 1);
        collectionsWaitUntil($page, "[...document.querySelectorAll('.filter-entry')].find(e => e.textContent.includes('Caixa'))?.classList.contains('is-empty') === true");

        expect($page->script("[...document.querySelectorAll('.filter-entry')].find(e => e.textContent.includes('Moldura')).querySelector('.filter-count').textContent"))->toBe('1');
    });

    it('shows the pieces when something is searched', function () {
        $page = collectionsOpen();
        $page->type('#filter-search', 'Joias');
        collectionsWaitForCards($page, 1);

        // The colourway is named after the piece too, so the name is read from the title line.
        $page->assertSeeIn('#product-grid .product-card-line', 'Caixa de Joias')
            ->assertSeeIn('#grid-crumbs [aria-current="page"]', 'Todas as peças');
    });

    it('opens straight on a collection from its link', function () {
        $page = collectionsOpen("/products?collection_id={$this->ids['filigree']['id']}");
        collectionsWaitForCards($page, 2);

        $page->assertSeeIn('#grid-crumbs [aria-current="page"]', 'Filigrana');
    });
});

describe('with no collections', function () {
    // Nothing to open first, so the page is the pieces alone, as it always was.
    it('shows the pieces straight away, with no breadcrumb', function () {
        makeProduct('Caixa');
        $page = collectionsOpen();

        expect(collectionsCards($page))->toBe(1)
            ->and(collectionsHidden($page, 'grid-crumbs'))->toBeTrue()
            ->and(collectionsHidden($page, 'collection-grid'))->toBeTrue();
    });
});

describe('on a phone', function () {
    beforeEach(fn () => collectionsSeed());

    it('lays the collections two across, without scrolling sideways', function () {
        $page = collectionsOpen('/products', 390, 780);
        $tops = $page->script("[...document.querySelectorAll('.collection-tile')].map(el => Math.round(el.getBoundingClientRect().top))");

        expect(count(array_unique($tops)))->toBe(2)
            ->and($page->script('document.documentElement.scrollWidth > window.innerWidth'))->toBeFalse('the catalogue must not scroll sideways');
    });
});
