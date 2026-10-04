<?php

use Illuminate\Support\Facades\DB;

/*
 * What the dashboard used to work out in the browser from the whole catalogue,
 * which stopped being possible past the API's hundred-row limit: how many pieces
 * each collection and colour set reaches, and which pieces have a photograph.
 */

beforeEach(fn () => signIn());

describe('has_photos', function () {
    beforeEach(function () {
        $this->bare = makeProduct('Sem fotografia');
        $this->shown = makeProduct('Com fotografia');
        $variant = makeVariant($this->shown);
        $this->postJson("/api/products/{$this->shown['id']}/images", ['variant_id' => $variant['id'], 'url' => '/static/img/a.jpg'])->assertCreated();
    });

    it('keeps only the pieces with a photograph, or only those without', function () {
        expect($this->getJson('/api/products/?has_photos=1')->json('products.*.name'))->toBe(['Com fotografia'])
            ->and($this->getJson('/api/products/?has_photos=0')->json('products.*.name'))->toBe(['Sem fotografia'])
            ->and($this->getJson('/api/products/')->json('pagination.total'))->toBe(2);
    });

    // A removed photograph is still a row, and must not count as one.
    it('does not count a removed photograph', function () {
        $image = DB::table('product_images')->value('id');
        $this->deleteJson("/api/products/{$this->shown['id']}/images/{$image}")->assertOk();

        expect($this->getJson('/api/products/?has_photos=0')->json('pagination.total'))->toBe(2);
    });

    it('counts under the other filters', function () {
        expect($this->getJson('/api/products/?has_photos=0&q=Com')->json('pagination.total'))->toBe(0);
    });
});

describe('pieces', function () {
    it('counts the pieces a colour set is offered in', function () {
        $set = makeColorSet('Preto e Branco');
        makeVariant(makeProduct('Caixa'), $set);
        makeVariant(makeProduct('Moldura'), $set);

        expect($this->getJson("/api/color-sets/{$set['id']}")->json('pieces'))->toBe(2)
            ->and($this->getJson('/api/color-sets/')->json('color_sets.0.pieces'))->toBe(2);
    });

    // Two of a piece's colourways in one collection are still one piece in it.
    it('counts each piece a collection reaches once', function () {
        $collection = makeCollection('Filigrana');
        $box = makeProduct('Caixa');
        putInCollection($box, $collection, 'Preto e Branco');
        putInCollection($box, $collection, 'Azul e Branco');
        putInCollection(makeProduct('Moldura'), $collection, 'Verde e Dourado');

        expect($this->getJson("/api/collections/{$collection['id']}")->json('pieces'))->toBe(2)
            ->and($this->getJson('/api/collections/')->json('collections.0.pieces'))->toBe(2);
    });

    it('counts nothing for an empty collection or set', function () {
        $collection = makeCollection('Vazia');
        $set = makeColorSet('Ninguém');

        expect($this->getJson("/api/collections/{$collection['id']}")->json('pieces'))->toBe(0)
            ->and($this->getJson("/api/color-sets/{$set['id']}")->json('pieces'))->toBe(0);
    });
});
