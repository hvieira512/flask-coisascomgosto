<?php

beforeEach(fn () => signIn());

function productsNames(string $uri): array
{
    return test()->getJson($uri)->json('products.*.name');
}

describe('listing', function () {
    it('answers an empty page on an empty table', function () {
        $body = $this->getJson('/api/products/')->json();

        expect($body['products'])->toBe([])->and($body['pagination']['total'])->toBe(0);
    });

    it('nests the materials', function () {
        $material = makeMaterial('Madeira');
        makeProduct('Vinho', materialIds: [$material['id']]);

        $product = $this->getJson('/api/products/')->json('products.0');
        expect($product['name'])->toBe('Vinho')
            ->and($product['materials'])->toBe([['id' => $material['id'], 'name' => 'Madeira']]);
    });

    it('lets a piece be made of several materials', function () {
        $wood = makeMaterial('Madeira');
        $paste = makeMaterial('Pasta de modelar');
        makeProduct('Manel e Maria', materialIds: [$wood['id'], $paste['id']]);

        expect($this->getJson('/api/products/')->json('products.0.materials.*.name'))->toBe(['Madeira', 'Pasta de modelar']);
    });

    it('gives a piece nobody classified no materials', function () {
        makeProduct('Vinho');

        expect($this->getJson('/api/products/')->json('products.0.materials'))->toBe([]);
    });

    it('searches the product name', function () {
        makeProduct('Vinho');
        makeProduct('Cerveja');

        expect(productsNames('/api/products/?q=Vin'))->toBe(['Vinho']);
    });

    // Material is descriptive and deliberately not searchable: a shopper looks
    // for a heart, not for wood.
    it('searches the type name', function () {
        $heart = makeProductType('Coracao de Viana');
        $box = makeProductType('Caixa');
        makeProduct('Vinho', typeId: $heart['id']);
        makeProduct('Bolo', typeId: $box['id']);

        expect(productsNames('/api/products/?q=Caix'))->toBe(['Bolo']);
    });

    // Regression: an unqualified `name` was ambiguous across the join.
    it('does not fail searching across the join', function () {
        makeProduct('Vinho');

        $this->getJson('/api/products/?q=Vinho')->assertOk();
    });

    it('counts only the matches in the total', function () {
        makeProduct('Vinho');
        makeProduct('Cerveja');

        expect($this->getJson('/api/products/?q=Vin')->json('pagination.total'))->toBe(1);
    });

    it('pages', function () {
        $material = makeMaterial('Madeira');
        foreach (['A', 'B', 'C'] as $name) {
            makeProduct($name, materialIds: [$material['id']]);
        }

        $body = $this->getJson('/api/products/?page=2&limit=2')->json();
        expect(array_column($body['products'], 'name'))->toBe(['C'])
            ->and($body['pagination'])->toBe(['total' => 3, 'page' => 2, 'pages' => 2, 'limit' => 2]);
    });

    it('refuses nonsense paging with 400', function (string $query) {
        $this->getJson("/api/products/{$query}")->assertStatus(400);
    })->with(['?page=abc', '?limit=0', '?page=0']);

    // The dashboard's order: an unphotographed piece stays where the owners
    // left it, so it is findable.
    it('keeps insertion order by default', function () {
        makeProduct('Sem fotografia');
        $photographed = makeProduct('Com fotografia');
        $this->postJson("/api/products/{$photographed['id']}/images", ['url' => '/a.jpg']);

        expect(productsNames('/api/products/'))->toBe(['Sem fotografia', 'Com fotografia']);
    });

    // The storefront's order: nobody should page past pieces with nothing to look at.
    it('puts photographed pieces first when asked', function () {
        makeProduct('Sem fotografia');
        $photographed = makeProduct('Com fotografia');
        $variant = makeVariant($photographed, makeColorSet('Branco', [makeColor('Branco')['id']]));
        $this->postJson("/api/products/{$photographed['id']}/images", ['url' => '/a.jpg', 'variant_id' => $variant['id']]);

        expect(productsNames('/api/products/?photographed_first=1'))->toBe(['Com fotografia', 'Sem fotografia']);
    });

    it('reads several type ids as OR', function () {
        $box = makeProductType('Caixa');
        $frame = makeProductType('Moldura');
        makeProduct('Caixa de Joias', typeId: $box['id']);
        makeProduct('Moldura Oval', typeId: $frame['id']);
        makeProduct('Outra coisa');

        $body = $this->getJson("/api/products/?type_id={$box['id']}&type_id={$frame['id']}")->json();
        $names = array_column($body['products'], 'name');
        sort($names);
        expect($names)->toBe(['Caixa de Joias', 'Moldura Oval'])
            ->and($body['pagination']['total'])->toBe(2);
    });

    it('still takes a single type id', function () {
        $box = makeProductType('Caixa');
        makeProduct('Caixa de Joias', typeId: $box['id']);
        makeProduct('Outra coisa');

        expect(productsNames("/api/products/?type_id={$box['id']}"))->toBe(['Caixa de Joias']);
    });

    it('ORs inside a filter and ANDs between them', function () {
        $box = makeProductType('Caixa');
        $frame = makeProductType('Moldura');
        $filigrana = makeCollection('Filigrana');
        putInCollection(makeProduct('Caixa Filigrana', typeId: $box['id']), $filigrana);
        makeProduct('Moldura sem colecção', typeId: $frame['id']);

        expect(productsNames("/api/products/?type_id={$box['id']}&type_id={$frame['id']}&collection_id={$filigrana['id']}"))
            ->toBe(['Caixa Filigrana']);
    });

    it('still pages photographed first without double-counting', function () {
        makeProduct('A');
        makeProduct('B');

        $body = $this->getJson('/api/products/?photographed_first=1&limit=1')->json();
        expect($body['pagination']['total'])->toBe(2)->and($body['products'])->toHaveCount(1);
    });
});

describe('creating', function () {
    it('creates and returns the product', function () {
        $material = makeMaterial('Madeira');

        $body = $this->postJson('/api/products/', [
            'name' => 'Vinho', 'description' => 'Tinto', 'type_id' => productType()['id'], 'material_ids' => [$material['id']],
        ])->assertCreated()->json();

        expect($body['name'])->toBe('Vinho')
            ->and($body['description'])->toBe('Tinto')
            ->and(array_column($body['materials'], 'name'))->toBe(['Madeira']);
    });

    it('answers 404 for an unknown material', function () {
        $this->postJson('/api/products/', [
            'name' => 'Vinho', 'description' => 'Tinto', 'type_id' => productType()['id'], 'material_ids' => [9999],
        ])->assertNotFound();
    });

    // Half-applied would be worse: the piece would be saved made of only the
    // material that happened to exist.
    it('refuses the whole list for one unknown material', function () {
        $material = makeMaterial('Madeira');

        $this->postJson('/api/products/', [
            'name' => 'Vinho', 'description' => 'Tinto', 'type_id' => productType()['id'], 'material_ids' => [$material['id'], 9999],
        ])->assertNotFound();
        $this->getJson('/api/products/')->assertJsonPath('products', []);
    });

    it('refuses a name already taken with 409', function () {
        $material = makeMaterial('Madeira');
        makeProduct('Vinho', materialIds: [$material['id']]);

        $this->postJson('/api/products/', [
            'name' => 'Vinho', 'description' => 'Outro', 'type_id' => productType()['id'], 'material_ids' => [$material['id']],
        ])->assertStatus(409);
    });

    it('refuses missing fields with 400', function (array $payload) {
        makeMaterial('Madeira');

        $this->postJson('/api/products/', $payload)->assertStatus(400);
    })->with([
        [['description' => 'Tinto', 'material_ids' => [1]]],
        [['name' => 'Vinho', 'material_ids' => [1]]],
        [['name' => 'Vinho', 'description' => 'Tinto']],
        [[]],
    ]);
});

describe('reading one', function () {
    it('returns it', function () {
        $made = makeProduct('Vinho');

        $this->getJson("/api/products/{$made['id']}")->assertJsonPath('name', 'Vinho');
    });

    it('answers 404 for an unknown id', function () {
        $this->getJson('/api/products/9999')->assertNotFound();
    });
});

describe('updating', function () {
    it('updates every field', function () {
        $made = makeProduct('Vinho');
        $other = makeMaterial('Tecido');

        $body = $this->putJson("/api/products/{$made['id']}", [
            'name' => 'Bolo', 'description' => 'Doce', 'type_id' => productType()['id'], 'material_ids' => [$other['id']],
        ])->assertOk()->json();

        expect($body['name'])->toBe('Bolo')
            ->and($body['description'])->toBe('Doce')
            ->and(array_column($body['materials'], 'name'))->toBe(['Tecido']);
    });

    it('replaces the materials with the ones sent', function () {
        $wood = makeMaterial('Madeira');
        $paste = makeMaterial('Pasta de modelar');
        $made = makeProduct('Manel e Maria', materialIds: [$wood['id'], $paste['id']]);

        $this->putJson("/api/products/{$made['id']}", [
            'name' => 'Manel e Maria', 'description' => 'd', 'type_id' => productType()['id'], 'material_ids' => [$paste['id']],
        ])->assertJsonPath('materials.0.name', 'Pasta de modelar')->assertJsonCount(1, 'materials');
    });

    it('leaves the piece unclassified when sent none', function () {
        $wood = makeMaterial('Madeira');
        $made = makeProduct('Vinho', materialIds: [$wood['id']]);

        $this->putJson("/api/products/{$made['id']}", [
            'name' => 'Vinho', 'description' => 'd', 'type_id' => productType()['id'], 'material_ids' => [],
        ])->assertJsonPath('materials', []);
    });

    // Regression: a missing product used to marshal to 200 with all-null fields.
    it('answers 404, not a null body, for an unknown product', function () {
        $material = makeMaterial('Madeira');

        $response = $this->putJson('/api/products/9999', [
            'name' => 'Ghost', 'description' => 'd', 'type_id' => productType()['id'], 'material_ids' => [$material['id']],
        ])->assertNotFound();
        expect($response->json('id'))->toBeNull();
    });

    it('answers 404 for an unknown material', function () {
        $made = makeProduct('Vinho');

        $this->putJson("/api/products/{$made['id']}", [
            'name' => 'Vinho', 'description' => 'd', 'type_id' => productType()['id'], 'material_ids' => [9999],
        ])->assertNotFound();
    });

    it('refuses a name another product has with 409', function () {
        $material = makeMaterial('Madeira');
        makeProduct('Vinho', materialIds: [$material['id']]);
        $other = makeProduct('Cerveja', materialIds: [$material['id']]);

        $this->putJson("/api/products/{$other['id']}", [
            'name' => 'Vinho', 'description' => 'd', 'type_id' => productType()['id'], 'material_ids' => [$material['id']],
        ])->assertStatus(409);
    });

    it('lets a product keep its own name', function () {
        $material = makeMaterial('Madeira');
        $made = makeProduct('Vinho', materialIds: [$material['id']]);

        $this->putJson("/api/products/{$made['id']}", [
            'name' => 'Vinho', 'description' => 'novo', 'type_id' => productType()['id'], 'material_ids' => [$material['id']],
        ])->assertOk();
    });

    it('refuses a partial body with 400', function () {
        $made = makeProduct('Vinho');

        $this->putJson("/api/products/{$made['id']}", ['name' => 'x'])->assertStatus(400);
    });
});

describe('deleting', function () {
    it('returns what it deleted, and it is gone', function () {
        $made = makeProduct('Vinho');

        $this->deleteJson("/api/products/{$made['id']}")->assertOk()->assertJsonPath('name', 'Vinho');
        $this->getJson("/api/products/{$made['id']}")->assertNotFound();
    });

    // Regression: the message used to read 'Category #... not found'.
    it('answers 404 naming the product for an unknown id', function () {
        $message = $this->deleteJson('/api/products/9999')->assertNotFound()->json('message');

        expect(strtolower($message))->toContain('product');
    });
});

// What the dashboard filter bar sends. Filtering on photographs happens on the
// fetched page in fetch.js, so it is deliberately absent here.
describe('dashboard filters', function () {
    it('narrows by name', function () {
        makeProduct('Bastidor Bordado');
        makeProduct('Caixa Redonda');

        expect(productsNames('/api/products/?q=bastidor&limit=100'))->toBe(['Bastidor Bordado']);
    });

    it('narrows to a type', function () {
        $box = makeProductType('Caixa');
        makeProduct('Caixa Redonda Filigrana', typeId: $box['id']);
        makeProduct('Outra');

        expect(productsNames("/api/products/?type_id={$box['id']}&limit=100"))->toBe(['Caixa Redonda Filigrana']);
    });

    it('narrows to a collection', function () {
        $collection = makeCollection('Bordados');
        putInCollection(makeProduct('Bastidor'), $collection);
        makeProduct('Sem colecção');

        expect(productsNames("/api/products/?collection_id={$collection['id']}&limit=100"))->toBe(['Bastidor']);
    });

    it('combines filters', function () {
        $collection = makeCollection('Bordados');
        putInCollection(makeProduct('Bastidor Bordado'), $collection);
        putInCollection(makeProduct('Bastidor Viana'), $collection);

        expect(productsNames("/api/products/?collection_id={$collection['id']}&q=viana&limit=100"))->toBe(['Bastidor Viana']);
    });

    it('answers an empty page, not an error, when nothing matches', function () {
        makeProduct('Caixa');

        $this->getJson('/api/products/?q=zzzz&limit=100')->assertOk()->assertJsonPath('products', []);
    });
});

describe('facets', function () {
    it('counts products per type', function () {
        $box = makeProductType('Caixa');
        $frame = makeProductType('Moldura');
        makeProduct('Caixa de Joias', typeId: $box['id']);
        makeProduct('Caixa de Garrafa', typeId: $box['id']);
        makeProduct('Moldura Oval', typeId: $frame['id']);

        $counts = productsFacetCounts('types');
        expect($counts[$box['id']])->toBe(2)->and($counts[$frame['id']])->toBe(1);
    });

    // The sidebar reads a missing id as zero and greys the entry out.
    it('leaves out an option with no products', function () {
        $spare = makeProductType('Tabuleiro');

        expect(productsFacetCounts('types'))->not->toHaveKey($spare['id']);
    });

    it('counts collections and materials too', function () {
        $collection = makeCollection('Filigrana');
        $material = makeMaterial('Madeira');
        putInCollection(makeProduct('Caixa', materialIds: [$material['id']]), $collection);

        expect(productsFacetCounts('collections'))->toBe([$collection['id'] => 1])
            ->and(productsFacetCounts('materials'))->toBe([$material['id'] => 1]);
    });

    // So the counts can add up to more than the catalogue holds, which is the
    // true answer to "how many pieces are made of wood".
    it('counts a piece of two materials under both', function () {
        $wood = makeMaterial('Madeira');
        $paste = makeMaterial('Pasta de modelar');
        makeProduct('Manel e Maria', materialIds: [$wood['id'], $paste['id']]);

        expect(productsFacetCounts('materials'))->toBe([$wood['id'] => 1, $paste['id'] => 1]);
    });

    it('is public', function () {
        $this->app['auth']->forgetGuards();
        $this->flushHeaders();

        $this->getJson('/api/products/facets')->assertOk();
    });
});

function productsFacetCounts(string $facet): array
{
    return collect(test()->getJson('/api/products/facets')->json($facet))->pluck('count', 'id')->all();
}
