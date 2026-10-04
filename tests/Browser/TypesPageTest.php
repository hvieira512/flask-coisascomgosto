<?php

/*
 * The dashboard's Tipos page: what families the catalogue is filed under, and
 * what the pieces are made of. Both are counted in SQL — counting in the browser
 * would have been quietly wrong past the hundred-product page limit.
 */

beforeEach(fn () => signIn());

function typesPageOpen(string $path = '/dashboard/types', string $ready = '#type-rows tr')
{
    $page = visit($path)->resize(1440, 1000);
    $page->assertPresent($ready);

    return $page;
}

function typesPageEditProduct(array $product)
{
    $row = "#product-list tr[data-product-id=\"{$product['id']}\"]";
    $page = typesPageOpen('/dashboard/products', $row);
    $page->click($row);
    $page->assertPresent('#pf-materials');

    return $page;
}

describe('the types ledger', function () {
    it('shows a count and a photograph of one of its pieces', function () {
        $box = makeProductType('Caixa');
        $product = makeProduct('Caixa Redonda', typeId: $box['id']);
        $variant = makeVariant($product, makeColorSet('Branco e Dourado'));
        $this->postJson("/api/products/{$product['id']}/images", ['variant_id' => $variant['id'], 'url' => '/static/img/caixa.jpg'])
            ->assertCreated();

        $row = "#type-rows tr[data-type-id=\"{$box['id']}\"]";
        $page = typesPageOpen(ready: $row);

        $page->assertSeeIn($row, '1 peça')
            ->assertAttribute("{$row} img.dash-thumb", 'src', '/static/img/caixa.jpg')
            ->assertNoJavaScriptErrors();
    });

    it('falls back to its drawing when no piece is photographed', function () {
        $heart = makeProductType('Coracao', icon: 'fa-heart');
        makeProduct('Coração de Viana', typeId: $heart['id']);

        $row = "#type-rows tr[data-type-id=\"{$heart['id']}\"]";
        typesPageOpen(ready: $row)
            ->assertCount("{$row} img.dash-thumb", 0)
            ->assertPresent("{$row} .dash-type-icon .fa-heart");
    });

    it('names the icon in the drawing column', function () {
        // The name is what the form asks for.
        makeProductType('Caixa', icon: 'fa-box');

        expect(typesPageOpen()->text('#type-rows tr'))->toContain('fa-box');
    });

    it('counts types and pieces in the head', function () {
        $box = makeProductType('Caixa');
        makeProductType('Moldura');
        makeProduct('Caixa Redonda', typeId: $box['id']);
        makeProduct('Caixa de Joias', typeId: $box['id']);

        typesPageOpen()->assertSeeIn('#type-count', '2 tipos · 2 peças');
    });

    it('says so when a type has no pieces', function () {
        makeProductType('Tabuleiro');

        expect(typesPageOpen()->text('#type-rows tr'))->toContain('Sem peças');
    });
});

describe('the materials panel', function () {
    it('counts the pieces made of each', function () {
        $wood = makeMaterial('Madeira');
        makeMaterial('Tecido');
        makeProduct('Caixa', materialIds: [$wood['id']]);
        makeProduct('Moldura', materialIds: [$wood['id']]);

        typesPageOpen(ready: '#material-rows li')
            ->assertSeeIn('#material-rows li:has-text("Madeira")', '2')
            ->assertSeeIn('#material-rows li:has-text("Tecido")', 'Nenhuma peça')
            ->assertNoJavaScriptErrors();
    });

    it('counts a piece of two materials under both', function () {
        $wood = makeMaterial('Madeira');
        $paste = makeMaterial('Pasta de modelar');
        makeProduct('Manel e Maria', materialIds: [$wood['id'], $paste['id']]);

        typesPageOpen(ready: '#material-rows li')
            ->assertSeeIn('#material-rows li:has-text("Madeira")', '1')
            ->assertSeeIn('#material-rows li:has-text("Pasta de modelar")', '1');
    });
});

// Chips, because a piece may be made of several materials.
describe('what a piece is made of', function () {
    it('keeps both materials of a piece made of two', function () {
        $wood = makeMaterial('Madeira');
        $paste = makeMaterial('Pasta de modelar');
        $product = makeProduct('Manel e Maria', materialIds: [$wood['id']]);

        $page = typesPageEditProduct($product)
            ->assertCount('#pf-materials .pick-chip', 2)
            ->assertAttribute("#pf-materials [data-pick=\"{$wood['id']}\"]", 'aria-pressed', 'true');

        $page->click("#pf-materials [data-pick=\"{$paste['id']}\"]");
        $page->click('#edit-submit');
        $page->assertMissing('#editProductModal.show');

        expect($this->getJson("/api/products/{$product['id']}")->json('materials.*.name'))->toBe(['Madeira', 'Pasta de modelar']);
        $page->assertNoJavaScriptErrors();
    });

    it('leaves the piece unclassified when every chip is unpressed', function () {
        // The list replaces what was there, so "none" has to be sendable.
        $wood = makeMaterial('Madeira');
        $product = makeProduct('Vinho', materialIds: [$wood['id']]);

        $page = typesPageEditProduct($product);
        $page->click("#pf-materials [data-pick=\"{$wood['id']}\"]");
        $page->click('#edit-submit');
        $page->assertMissing('#editProductModal.show');

        expect($this->getJson("/api/products/{$product['id']}")->json('materials'))->toBe([]);
    });
});
