<?php

/*
 * What the Flask repository layer promised, checked where Laravel keeps it: the
 * API for what the owners see, the models for what has no endpoint of its own.
 */

use App\Models\ColorSet;
use App\Models\Product;
use App\Models\ProductImage;
use App\Models\ProductType;
use App\Models\ProductVariant;
use App\Models\User;
use Illuminate\Support\Facades\DB;

describe('materials', function () {
    beforeEach(fn () => signIn());

    it('ignores a blank search', function (string $blank) {
        makeMaterial('Madeira');

        expect($this->getJson("/api/materials/?q={$blank}")->json('pagination.total'))->toBe(1);
    })->with(['', '%20%20%20']);
});

describe('products', function () {
    beforeEach(fn () => signIn());

    it('nests the type and materials', function () {
        $type = makeProductType('Caixa');
        $material = makeMaterial('Madeira');
        $product = makeProduct('Vinho', 'Tinto', $type['id'], [$material['id']]);

        $this->getJson("/api/products/{$product['id']}")->assertExactJson([
            'id' => $product['id'],
            'name' => 'Vinho',
            'description' => 'Tinto',
            'materials' => [['id' => $material['id'], 'name' => 'Madeira']],
            'type' => ['id' => $type['id'], 'name' => 'Caixa', 'icon' => 'fa-box'],
            'collections' => [],
            'default_size' => null,
            'sizes' => [],
            'variants' => [],
            'primary_image' => null,
        ]);
    });

    it('replaces and deduplicates the materials', function () {
        $wood = makeMaterial('Madeira');
        $paste = makeMaterial('Pasta de modelar');
        $product = makeProduct('Manel e Maria', '');
        $save = fn (array $ids) => $this->putJson("/api/products/{$product['id']}", [
            'name' => 'Manel e Maria', 'description' => '', 'type_id' => $product['type']['id'], 'material_ids' => $ids,
        ])->assertOk()->json('materials.*.name');

        expect($save([$wood['id'], $paste['id'], $wood['id']]))->toBe(['Madeira', 'Pasta de modelar'])
            ->and($save([$paste['id']]))->toBe(['Pasta de modelar'])
            ->and($save([]))->toBe([]);
    });

    it('answers 404 for an unknown id', function () {
        $this->getJson('/api/products/9999')->assertNotFound();
    });

    // A shopper looking for "madeira" wants pieces named that, not every wooden thing.
    it('does not search by material name', function () {
        makeProduct('Vinho', '', materialIds: [makeMaterial('Madeira')['id']]);

        expect($this->getJson('/api/products/?q=Madeira')->json('products'))->toBe([]);
    });

    it('searches by name, and the total counts the matches', function () {
        makeProduct('Vinho', '');
        makeProduct('Cerveja', '');

        $body = $this->getJson('/api/products/?q=Vin')->json();

        expect(array_column($body['products'], 'name'))->toBe(['Vinho'])
            ->and($body['pagination']['total'])->toBe(1)
            ->and($this->getJson('/api/products/')->json('pagination.total'))->toBe(2);
    });

    it('refuses a name another piece has, but lets a piece keep its own', function () {
        $product = makeProduct('Vinho', '');
        $other = makeProduct('Cerveja', '');
        $payload = ['name' => 'Vinho', 'description' => '', 'type_id' => $product['type']['id']];

        $this->putJson("/api/products/{$other['id']}", $payload)->assertStatus(409);
        $this->putJson("/api/products/{$product['id']}", $payload)->assertOk();
    });

    it('overwrites the fields on update', function () {
        $wood = makeMaterial('Madeira');
        $cloth = makeMaterial('Tecido');
        $product = makeProduct('Vinho', 'Tinto', materialIds: [$wood['id']]);

        $this->putJson("/api/products/{$product['id']}", [
            'name' => 'Bolo', 'description' => 'Doce', 'type_id' => $product['type']['id'], 'material_ids' => [$cloth['id']],
        ])->assertOk();

        $updated = $this->getJson("/api/products/{$product['id']}")->json();
        expect($updated['name'])->toBe('Bolo')
            ->and(array_column($updated['materials'], 'id'))->toBe([$cloth['id']]);
    });

    it('deletes', function () {
        $product = makeProduct('V', '');

        $this->deleteJson("/api/products/{$product['id']}")->assertOk();
        $this->getJson("/api/products/{$product['id']}")->assertNotFound();
    });

    // A material is not structural: the piece survives, unclassified.
    it('detaches a deleted material from its pieces', function () {
        $material = makeMaterial('Madeira');
        $product = makeProduct('Vinho', '', materialIds: [$material['id']]);

        $this->deleteJson("/api/materials/{$material['id']}")->assertOk();

        expect($this->getJson('/api/products/')->json('pagination.total'))->toBe(1)
            ->and($this->getJson("/api/products/{$product['id']}")->json('materials'))->toBe([])
            ->and(DB::table('product_materials')->where('product_id', $product['id'])->exists())->toBeFalse();
    });
});

/*
 * The landing page's type cards. A type with nothing photographed gets no cover
 * and falls back to its icon.
 */
function repositoriesPhotograph(Product $product, string $colour, array $image): void
{
    $set = ColorSet::firstOrCreate(['name' => $colour]);
    $variant = ProductVariant::firstOrCreate(['product_id' => $product->id, 'color_set_id' => $set->id]);
    ProductImage::create(['product_id' => $product->id, 'variant_id' => $variant->id] + $image + ['position' => 0]);
}

describe('product type covers', function () {
    it('takes the first photograph of the earliest piece', function () {
        $box = ProductType::create(['name' => 'Caixa']);
        $first = Product::create(['type_id' => $box->id, 'name' => 'Caixa alta', 'description' => '']);
        $second = Product::create(['type_id' => $box->id, 'name' => 'Caixa baixa', 'description' => '']);

        repositoriesPhotograph($second, 'Azul', ['url' => '/second.jpg']);
        repositoriesPhotograph($first, 'Branco', ['url' => '/late.jpg', 'position' => 3]);
        repositoriesPhotograph($first, 'Branco', ['url' => '/cover.jpg', 'alt' => 'Uma caixa', 'position' => 1]);

        expect(ProductType::covers([$box->id]))->toBe([$box->id => ['url' => '/cover.jpg', 'alt' => 'Uma caixa']]);
    });

    it("falls back to the piece's name for the alt", function () {
        $box = ProductType::create(['name' => 'Caixa']);
        repositoriesPhotograph(Product::create(['type_id' => $box->id, 'name' => 'Caixa de joias', 'description' => '']), 'Branco', ['url' => '/x.jpg']);

        expect(ProductType::covers([$box->id])[$box->id]['alt'])->toBe('Caixa de joias');
    });

    it('leaves out a type with no photographs', function () {
        $box = ProductType::create(['name' => 'Caixa']);
        Product::create(['type_id' => $box->id, 'name' => 'Caixa de joias', 'description' => '']);

        expect(ProductType::covers([$box->id]))->toBe([]);
    });

    it('asks nothing of the database for no types', function () {
        DB::enableQueryLog();

        expect(ProductType::covers([]))->toBe([])
            ->and(DB::getQueryLog())->toBe([]);
    });
});

describe('users', function () {
    it('reads back an account', function () {
        $alice = makeUser('alice', email: 'alice@example.com');
        signIn($alice);

        $this->getJson("/api/users/{$alice->id}")
            ->assertOk()
            ->assertJsonPath('username', 'alice')
            ->assertJsonPath('email', 'alice@example.com');
    });

    it('never exposes the password', function () {
        $alice = signIn(makeUser('alice'));

        expect($this->getJson("/api/users/{$alice->id}")->json())->not->toHaveKey('password')
            ->and($this->getJson('/api/users')->json('users.0'))->not->toHaveKey('password');
    });

    // One kind of account: everyone who can sign in can do everything.
    it('carries no role', function () {
        $alice = signIn(makeUser('alice'));

        expect(array_keys($this->getJson("/api/users/{$alice->id}")->json()))
            ->toEqualCanonicalizing(['id', 'username', 'email', 'created_at']);
    });

    it('counts and pages', function () {
        foreach (['alice', 'bob', 'carol'] as $name) {
            makeUser($name);
        }
        signIn(User::first());

        $body = $this->getJson('/api/users?page=2&limit=2')->json();

        expect(array_column($body['users'], 'username'))->toBe(['carol'])
            ->and($body['pagination']['total'])->toBe(3);
    });
});
