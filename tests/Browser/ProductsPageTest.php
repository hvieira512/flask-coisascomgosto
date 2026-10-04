<?php

use App\Models\Product;
use App\Models\ProductImage;
use App\Models\ProductVariant;

/*
 * The dashboard's list of pieces pages through the catalogue and asks the server
 * for its counts. It used to load every piece, and stopped working at the API's
 * hundred-row limit.
 */

beforeEach(function () {
    signIn();
    $type = productType();
    foreach (range(1, 55) as $n) {
        Product::create(['name' => sprintf('Peça %02d', $n), 'description' => '', 'type_id' => $type['id']]);
    }

    $photographed = Product::firstWhere('name', 'Peça 01');
    $variant = ProductVariant::create(['product_id' => $photographed->id, 'color_set_id' => makeColorSet('Branco')['id']]);
    ProductImage::create(['product_id' => $photographed->id, 'variant_id' => $variant->id, 'url' => '/static/img/a.jpg']);
});

function productsPageRows($page): int
{
    return $page->script("() => document.querySelectorAll('#product-list tr[data-product-id]').length");
}

/** The list re-renders after a fetch; Pest's assertions read once and do not wait. */
function productsPageWaitFor($page, string $js): void
{
    for ($i = 0; $i < 100 && ! $page->script("() => {$js}"); $i++) {
        $page->wait(0.05);
    }
    expect($page->script("() => {$js}"))->toBeTrue("timed out waiting for: {$js}");
}

function productsPageOpen()
{
    $page = visit('/dashboard/products')->resize(1280, 900);
    $page->assertPresent('#product-list tr[data-product-id]');

    return $page;
}

it('shows the first page, and counts the whole catalogue', function () {
    $page = productsPageOpen();

    expect(productsPageRows($page))->toBe(50);
    $page->assertSeeIn('#product-count', '55 peças')
        ->assertSeeIn('#product-count', '54 sem fotografia')
        ->assertVisible('#product-pager')
        ->assertSeeIn('#pager-label', 'Página 1 de 2')
        ->assertNoJavaScriptErrors();
});

it('moves between pages', function () {
    $page = productsPageOpen();

    $page->click('#pager-next');
    productsPageWaitFor($page, "document.querySelectorAll('#product-list tr[data-product-id]').length === 5");
    $page->assertSeeIn('#pager-label', 'Página 2 de 2')->assertSee('Peça 55');

    $page->click('#pager-prev');
    productsPageWaitFor($page, "document.querySelectorAll('#product-list tr[data-product-id]').length === 50");
    $page->assertSeeIn('#pager-label', 'Página 1 de 2')->assertSee('Peça 01');
});

it('shows a collection name in the filter as text, not markup', function () {
    makeCollection('<b>Negrito</b>');
    $page = productsPageOpen();

    expect($page->script("() => [...document.querySelectorAll('#filter-collection option')].map((o) => o.textContent)"))
        ->toContain('<b>Negrito</b>');
});

it('filters by photograph on the server, back on the first page', function () {
    $page = productsPageOpen();
    $page->click('#pager-next');
    productsPageWaitFor($page, "document.querySelectorAll('#product-list tr[data-product-id]').length === 5");

    $page->select('#filter-photos', 'some');
    productsPageWaitFor($page, "document.querySelectorAll('#product-list tr[data-product-id]').length === 1");

    $page->assertSee('Peça 01')->assertMissing('#product-pager')->assertSeeIn('#product-count', '1 peça');
});
