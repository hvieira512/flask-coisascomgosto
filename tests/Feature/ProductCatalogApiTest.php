<?php

/*
 * How products compose the catalogue layers: types, collections, colour-set
 * variants and sizes. The worked example is a "Caixa Redonda" in the Barra da
 * Saia collection, offered in four colour sets.
 */

beforeEach(fn () => signIn());

function catalogRoundBox(): array
{
    $collection = makeCollection('Barra da Saia');
    $colors = [];
    foreach (['White', 'Green', 'Red', 'Blue', 'Gray'] as $name) {
        $colors[$name] = makeColor($name)['id'];
    }
    $pairs = [
        'White and Green' => ['White', 'Green'],
        'Red and White' => ['Red', 'White'],
        'Blue and White' => ['Blue', 'White'],
        'White and Gray' => ['White', 'Gray'],
    ];
    $colorSets = [];
    foreach ($pairs as $name => $members) {
        $colorSets[] = makeColorSet($name, array_map(fn ($c) => $colors[$c], $members), [$collection['id']]);
    }

    $product = makeProduct('Caixa Redonda');
    foreach ($colorSets as $set) {
        makeVariant($product, $set);
    }

    return ['product' => $product, 'collection' => $collection, 'color_sets' => $colorSets, 'colors' => $colors];
}

function catalogNames(string $uri): array
{
    return test()->getJson($uri)->json('products.*.name');
}

describe('product type', function () {
    it('carries its type', function () {
        $type = makeProductType('Hairbrush');
        $product = makeProduct('Escova', typeId: $type['id']);

        // Resolved, not passed through: "Hairbrush" matches the brush keyword.
        $this->getJson("/api/products/{$product['id']}")
            ->assertJsonPath('type', ['id' => $type['id'], 'name' => 'Hairbrush', 'icon' => 'fa-brush']);
    });

    it('is required', function () {
        $material = makeMaterial('Madeira');

        $this->postJson('/api/products/', ['name' => 'Sem tipo', 'description' => 'd', 'material_ids' => [$material['id']]])
            ->assertStatus(400);
    });

    it('answers 404 for an unknown type', function () {
        $material = makeMaterial('Madeira');

        $this->postJson('/api/products/', ['name' => 'Ghost', 'description' => 'd', 'material_ids' => [$material['id']], 'type_id' => 9999])
            ->assertNotFound();
    });

    it('filters by type', function () {
        $brush = makeProductType('Hairbrush');
        $frame = makeProductType('Picture frame');
        makeProduct('Escova', typeId: $brush['id']);
        makeProduct('Moldura', typeId: $frame['id']);

        expect(catalogNames("/api/products/?type_id={$brush['id']}"))->toBe(['Escova']);
    });

    // A family holds the pieces directly: "Caixa" is the type, and "Caixa
    // rectangular" is one of its pieces.
    it('returns every piece of the family when filtering by type', function () {
        $box = makeProductType('Caixa');
        makeProduct('Caixa rectangular', typeId: $box['id']);
        makeProduct('Caixa de Joias', typeId: $box['id']);
        makeProduct('Escova');

        $body = $this->getJson("/api/products/?type_id={$box['id']}")->json();
        $names = array_column($body['products'], 'name');
        sort($names);
        expect($names)->toBe(['Caixa de Joias', 'Caixa rectangular'])
            ->and($body['pagination']['total'])->toBe(2);
    });

    // type_id is NOT NULL, so there is no unfiled state to move the piece into:
    // refusing beats destroying it.
    it('refuses to delete a type still in use with 409', function () {
        $brush = makeProductType('Hairbrush');
        $product = makeProduct('Escova', typeId: $brush['id']);

        $message = $this->deleteJson("/api/product-types/{$brush['id']}")->assertStatus(409)->json('message');
        expect($message)->toContain('1 product');

        $this->getJson("/api/product-types/{$brush['id']}")->assertOk();
        $this->getJson("/api/products/{$product['id']}")->assertOk();
    });

    it('names the number of products in the refusal', function () {
        $brush = makeProductType('Escova de cabelo');
        makeProduct('Escova A', typeId: $brush['id']);
        makeProduct('Escova B', typeId: $brush['id']);

        expect($this->deleteJson("/api/product-types/{$brush['id']}")->json('message'))->toContain('2 products still use');
    });

    it('deletes an unused type', function () {
        $spare = makeProductType('Tabuleiro');

        $this->deleteJson("/api/product-types/{$spare['id']}")->assertOk();
        $this->getJson("/api/product-types/{$spare['id']}")->assertNotFound();
    });
});

describe('variants', function () {
    it('lists all four', function () {
        $box = catalogRoundBox();

        expect($this->getJson("/api/products/{$box['product']['id']}")->json('variants.*.color_set.name'))
            ->toBe(['White and Green', 'Red and White', 'Blue and White', 'White and Gray']);
    });

    it('nests the colours of each in order', function () {
        $box = catalogRoundBox();

        $variants = collect($this->getJson("/api/products/{$box['product']['id']}/variants")->json('variants'));
        $first = $variants->firstWhere('color_set.name', 'White and Green');
        expect(array_column($first['color_set']['colors'], 'name'))->toBe(['White', 'Green']);
    });

    // A colour set may be gathered by several collections, and a variant has no
    // use for them: the storefront filters by the product's collections.
    it('names its colour set and nothing about collections', function () {
        $box = catalogRoundBox();

        $set = $this->getJson("/api/products/{$box['product']['id']}/variants")->json('variants.0.color_set');
        expect($set['name'])->toBe('White and Green')
            ->and($set)->not->toHaveKey('collection')
            ->and($set)->not->toHaveKey('collections');
    });

    it('refuses the same colour set twice with 409', function () {
        $box = catalogRoundBox();

        $this->postJson("/api/products/{$box['product']['id']}/variants", ['color_set_id' => $box['color_sets'][0]['id']])
            ->assertStatus(409);
    });

    it('answers 404 for an unknown colour set', function () {
        $product = makeProduct('Caixa');

        $this->postJson("/api/products/{$product['id']}/variants", ['color_set_id' => 9999])->assertNotFound();
    });

    it('answers 404 for an unknown product', function () {
        $set = makeColorSet('White and Green');

        $this->getJson('/api/products/9999/variants')->assertNotFound();
        $this->postJson('/api/products/9999/variants', ['color_set_id' => $set['id']])->assertNotFound();
    });

    it('deletes only that variant', function () {
        $box = catalogRoundBox();
        $id = $box['product']['id'];
        $variant = $this->getJson("/api/products/{$id}/variants")->json('variants.0');

        $this->deleteJson("/api/products/{$id}/variants/{$variant['id']}")->assertOk();

        $this->getJson("/api/products/{$id}/variants")->assertJsonCount(3, 'variants');
    });

    it('cannot delete a variant of another product', function () {
        $box = catalogRoundBox();
        $other = makeProduct('Outra caixa');
        $variant = $this->getJson("/api/products/{$box['product']['id']}/variants")->json('variants.0');

        $this->deleteJson("/api/products/{$other['id']}/variants/{$variant['id']}")->assertNotFound();
    });

    it('goes when its colour set is deleted', function () {
        $box = catalogRoundBox();

        $this->deleteJson("/api/color-sets/{$box['color_sets'][0]['id']}");

        $this->getJson("/api/products/{$box['product']['id']}")->assertJsonCount(3, 'variants');
    });

    it('goes with the product', function () {
        $box = catalogRoundBox();

        $this->deleteJson("/api/products/{$box['product']['id']}");

        $this->getJson("/api/products/{$box['product']['id']}/variants")->assertNotFound();
    });
});

describe('sizes', function () {
    it('takes a default size', function () {
        $product = makeProduct('Caixa', defaultSizeId: sizes()['Médio']['id']);

        $this->getJson("/api/products/{$product['id']}")->assertJsonPath('default_size.name', 'Médio');
    });

    it('needs no default size', function () {
        $product = makeProduct('Caixa');

        $this->getJson("/api/products/{$product['id']}")->assertJsonPath('default_size', null);
    });

    it('answers 404 for an unknown default size', function () {
        $material = makeMaterial('Madeira');

        $this->postJson('/api/products/', [
            'name' => 'Ghost', 'description' => 'd', 'type_id' => productType()['id'],
            'material_ids' => [$material['id']], 'default_size_id' => 9999,
        ])->assertNotFound();
    });

    it('starts with none', function () {
        $product = makeProduct('Caixa');

        $this->getJson("/api/products/{$product['id']}/sizes")->assertExactJson([]);
    });

    it('can be assigned', function () {
        $sizes = sizes();
        $product = makeProduct('Caixa');

        $response = $this->putJson("/api/products/{$product['id']}/sizes", [
            'size_ids' => [$sizes['Pequeno']['id'], $sizes['Médio']['id'], $sizes['Grande']['id']],
        ])->assertOk();
        expect(array_column($response->json(), 'name'))->toBe(['Pequeno', 'Médio', 'Grande']);
    });

    it('come back in display order', function () {
        $sizes = sizes();
        $product = makeProduct('Caixa');
        $this->putJson("/api/products/{$product['id']}/sizes", ['size_ids' => [$sizes['Grande']['id'], $sizes['Pequeno']['id']]]);

        expect(array_column($this->getJson("/api/products/{$product['id']}/sizes")->json(), 'name'))->toBe(['Pequeno', 'Grande']);
    });

    it('appear on the product', function () {
        $sizes = sizes();
        $product = makeProduct('Caixa');
        $this->putJson("/api/products/{$product['id']}/sizes", ['size_ids' => [$sizes['Pequeno']['id'], $sizes['Médio']['id']]]);

        expect($this->getJson("/api/products/{$product['id']}")->json('sizes.*.name'))->toBe(['Pequeno', 'Médio']);
    });

    it('are replaced, not appended, by a PUT', function () {
        $sizes = sizes();
        $product = makeProduct('Caixa');
        $this->putJson("/api/products/{$product['id']}/sizes", ['size_ids' => [$sizes['Pequeno']['id'], $sizes['Médio']['id']]]);

        $response = $this->putJson("/api/products/{$product['id']}/sizes", ['size_ids' => [$sizes['Grande']['id']]]);
        expect(array_column($response->json(), 'name'))->toBe(['Grande']);
    });

    it('are cleared by an empty list', function () {
        $sizes = sizes();
        $product = makeProduct('Caixa');
        $this->putJson("/api/products/{$product['id']}/sizes", ['size_ids' => [$sizes['Pequeno']['id']]]);

        $this->putJson("/api/products/{$product['id']}/sizes", ['size_ids' => []])->assertExactJson([]);
    });

    it('answer 404 for an unknown size', function () {
        $product = makeProduct('Caixa');

        $this->putJson("/api/products/{$product['id']}/sizes", ['size_ids' => [9999]])->assertNotFound();
    });

    it('answer 404 for an unknown product', function () {
        $sizes = sizes();

        $this->getJson('/api/products/9999/sizes')->assertNotFound();
        $this->putJson('/api/products/9999/sizes', ['size_ids' => [$sizes['Pequeno']['id']]])->assertNotFound();
    });

    it('come off the products when deleted', function () {
        $sizes = sizes();
        $product = makeProduct('Caixa');
        $this->putJson("/api/products/{$product['id']}/sizes", ['size_ids' => [$sizes['Pequeno']['id'], $sizes['Médio']['id']]]);

        $this->deleteJson("/api/sizes/{$sizes['Pequeno']['id']}");

        expect(array_column($this->getJson("/api/products/{$product['id']}/sizes")->json(), 'name'))->toBe(['Médio']);
    });

    it('clear the default when it is deleted', function () {
        $sizes = sizes();
        $product = makeProduct('Caixa', defaultSizeId: $sizes['Médio']['id']);

        $this->deleteJson("/api/sizes/{$sizes['Médio']['id']}");

        $this->getJson("/api/products/{$product['id']}")->assertJsonPath('default_size', null);
    });
});

// A piece is in a collection because one of its colourways is. All four of the
// round box's colour sets are gathered by Barra da Saia, and it is in it once.
describe('collections and filters', function () {
    it('carries the collections its colours are in', function () {
        $box = catalogRoundBox();

        expect($this->getJson("/api/products/{$box['product']['id']}")->json('collections.*.name'))->toBe(['Barra da Saia']);
    });

    it('puts a piece whose colours are in none in none', function () {
        $product = makeProduct('Sem colecção');
        makeVariant($product, makeColorSet('Cor solta', [makeColor('Tom')['id']]));

        $this->getJson("/api/products/{$product['id']}")->assertJsonPath('collections', []);
    });

    // An old client still sending collection_id is not refused, just not
    // listened to. The alternative reading is that the field still works.
    it('ignores a collection sent with a piece', function () {
        $collection = makeCollection('Filigrana');

        $this->postJson('/api/products/', [
            'name' => 'Ghost', 'description' => 'd', 'type_id' => productType()['id'], 'collection_id' => $collection['id'],
        ])->assertCreated()->assertJsonPath('collections', []);
    });

    it('filters by collection', function () {
        $box = catalogRoundBox();
        makeProduct('Fora da coleccao');

        $body = $this->getJson("/api/products/?collection_id={$box['collection']['id']}")->json();
        expect(array_column($body['products'], 'name'))->toBe(['Caixa Redonda'])
            ->and($body['pagination']['total'])->toBe(1);
    });

    it('filters by material', function () {
        $madeira = makeMaterial('Madeira');
        $tecido = makeMaterial('Tecido');
        makeProduct('Caixa', materialIds: [$madeira['id']]);
        makeProduct('Lenco', materialIds: [$tecido['id']]);

        expect(catalogNames("/api/products/?material_id={$madeira['id']}"))->toBe(['Caixa']);
    });

    // And exactly once: matching through a JOIN would return it twice.
    it('finds a piece of two materials under either', function () {
        $madeira = makeMaterial('Madeira');
        $pasta = makeMaterial('Pasta de modelar');
        makeProduct('Manel e Maria', materialIds: [$madeira['id'], $pasta['id']]);

        foreach ([$madeira, $pasta] as $material) {
            $body = $this->getJson("/api/products/?material_id={$material['id']}")->json();
            expect(array_column($body['products'], 'name'))->toBe(['Manel e Maria'])
                ->and($body['pagination']['total'])->toBe(1);
        }

        expect(catalogNames("/api/products/?material_id={$madeira['id']}&material_id={$pasta['id']}"))->toBe(['Manel e Maria']);
    });

    it('searches the type name', function () {
        $brush = makeProductType('Hairbrush');
        makeProduct('Escova', typeId: $brush['id']);
        makeProduct('Moldura');

        expect(catalogNames('/api/products/?q=Hairbrush'))->toBe(['Escova']);
    });

    it('resolves variants for every row of the list', function () {
        catalogRoundBox();
        makeProduct('Sem variantes');

        $byName = collect($this->getJson('/api/products/')->json('products'))->keyBy('name');
        expect($byName['Caixa Redonda']['variants'])->toHaveCount(4)
            ->and($byName['Sem variantes']['variants'])->toBe([]);
    });
});
