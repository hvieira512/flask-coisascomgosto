<?php

/*
 * Every foreign key restates a cascade the models already perform, and two
 * statements of one rule drift unless something compares them. These tests go
 * around the models on purpose: a plain DELETE is the case the constraints exist
 * for — the manual SQL session, the future script.
 */

use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;

// Kept as data so a new relationship without a rule shows up as a missing row.
const REFERENTIAL_EXPECTED_RULES = [
    'products.type_id' => 'RESTRICT',
    'products.default_size_id' => 'SET NULL',
    // A colour set is shared: deleting a collection unlinks it and the set survives.
    'collection_color_sets.collection_id' => 'CASCADE',
    'collection_color_sets.color_set_id' => 'CASCADE',
    'color_set_colors.color_set_id' => 'CASCADE',
    'color_set_colors.color_id' => 'CASCADE',
    'product_variants.product_id' => 'CASCADE',
    'product_variants.color_set_id' => 'CASCADE',
    'product_images.product_id' => 'CASCADE',
    'product_images.variant_id' => 'CASCADE',
    'product_sizes.product_id' => 'CASCADE',
    'product_sizes.size_id' => 'CASCADE',
    'product_materials.product_id' => 'CASCADE',
    'product_materials.material_id' => 'CASCADE',
    // A view count for a deleted piece answers nothing; a deleted colour or size
    // does not take the enquiry, which still counts for the piece.
    'storefront_events.product_id' => 'CASCADE',
    'storefront_events.variant_id' => 'SET NULL',
    'storefront_events.size_id' => 'SET NULL',
];

function referentialRules(): array
{
    return collect(DB::select(
        'SELECT rc.delete_rule AS rule_name, kcu.table_name AS tbl, kcu.column_name AS col
         FROM information_schema.referential_constraints rc
         JOIN information_schema.key_column_usage kcu
           ON kcu.constraint_name = rc.constraint_name
          AND kcu.constraint_schema = rc.constraint_schema
         WHERE rc.constraint_schema = DATABASE()'
    ))->mapWithKeys(fn ($row) => ["{$row->tbl}.{$row->col}" => $row->rule_name])->all();
}

/** A product with a colour: one of the things that hang off it. */
function referentialPiece(): array
{
    $product = makeProduct('Caixa com tudo');
    $colorSet = makeColorSet('Azul e Dourado');

    return [$product, $colorSet, makeVariant($product, $colorSet)];
}

beforeEach(fn () => signIn());

it('declares exactly the rules the models follow', function () {
    $actual = referentialRules();
    $expected = REFERENTIAL_EXPECTED_RULES;
    ksort($actual);
    ksort($expected);

    expect($actual)->toBe($expected);
});

it('refuses an orphan', function (string $sql) {
    DB::insert($sql);
})->throws(QueryException::class)->with([
    'INSERT INTO product_variants (product_id, color_set_id) VALUES (9999, 1)',
    "INSERT INTO product_images (product_id, variant_id, url) VALUES (9999, 9999, '/x.jpg')",
    'INSERT INTO product_sizes (product_id, size_id) VALUES (9999, 1)',
    'INSERT INTO color_set_colors (color_set_id, color_id) VALUES (9999, 1)',
]);

describe('deleting cascades the way the models would', function () {
    it('takes the variants with a product', function () {
        [$product, , $variant] = referentialPiece();

        DB::table('products')->where('id', $product['id'])->delete();

        expect(DB::table('product_variants')->where('id', $variant['id'])->exists())->toBeFalse();
    });

    it('takes the variants using a colour set', function () {
        [, $colorSet, $variant] = referentialPiece();

        DB::table('color_sets')->where('id', $colorSet['id'])->delete();

        expect(DB::table('product_variants')->where('id', $variant['id'])->exists())->toBeFalse();
    });

    it('takes the photographs with a variant', function () {
        [$product, , $variant] = referentialPiece();
        DB::table('product_images')->insert(['product_id' => $product['id'], 'variant_id' => $variant['id'], 'url' => '/static/img/products/x.jpg']);

        DB::table('product_variants')->where('id', $variant['id'])->delete();

        expect(DB::table('product_images')->where('variant_id', $variant['id'])->exists())->toBeFalse();
    });

    // The cascade falls on the join row, the only thing that said the piece was
    // in it: losing a piece because a grouping went away would be the worst
    // possible reading of a cascade.
    it('leaves the piece and its colour when a collection goes', function () {
        $collection = makeCollection('Inverno');
        $product = makeProduct('Caixa de Inverno');
        $colorSet = putInCollection($product, $collection);

        DB::table('collections')->where('id', $collection['id'])->delete();

        expect(DB::table('products')->where('id', $product['id'])->exists())->toBeTrue()
            ->and(DB::table('color_sets')->where('id', $colorSet['id'])->exists())->toBeTrue()
            ->and(DB::table('collection_color_sets')->where('collection_id', $collection['id'])->exists())->toBeFalse();
    });

    it('detaches rather than deletes when a material goes', function () {
        $material = makeMaterial('Cortiça');
        $product = makeProduct('Caixa de cortiça', materialIds: [$material['id']]);

        DB::table('materials')->where('id', $material['id'])->delete();

        expect(DB::table('products')->where('id', $product['id'])->exists())->toBeTrue()
            ->and(DB::table('product_materials')->where('product_id', $product['id'])->exists())->toBeFalse();
    });
});

describe('a type in use', function () {
    // type_id is NOT NULL, so there is no unfiled state: a cascade would delete
    // the owners' work.
    it('cannot be deleted by the database', function () {
        $type = makeProductType('Tipo em uso');
        makeProduct('Peça desse tipo', typeId: $type['id']);

        DB::table('product_types')->where('id', $type['id'])->delete();
    })->throws(QueryException::class);

    it('is refused by the API with 409 and the count', function () {
        $type = makeProductType('Tipo em uso');
        makeProduct('Peça desse tipo', typeId: $type['id']);

        expect($this->deleteJson("/api/product-types/{$type['id']}")->assertStatus(409)->json('message'))->toContain('1');
    });

    it('still goes when unused', function () {
        $type = makeProductType('Tipo sem peças');

        $this->deleteJson("/api/product-types/{$type['id']}")->assertOk();
    });
});
