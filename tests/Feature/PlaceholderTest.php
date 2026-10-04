<?php

use App\Support\TypeIcons;

/*
 * The tile a piece with no photograph gets: a wash of its first colour with its
 * type's icon, drawn by static/js/store/placeholder.js. The icon is resolved on
 * the server (App\Support\TypeIcons), which is what most of this covers.
 */

beforeEach(fn () => signIn());

describe('a product type icon', function () {
    it('round-trips', function () {
        $this->postJson('/api/product-types/', ['name' => 'Coração', 'icon' => 'fa-heart'])
            ->assertCreated()->assertJsonPath('icon', 'fa-heart');
    });

    it('is optional', function () {
        expect(makeProductType('Sem ícone')['icon'])->toBeNull();
    });

    it('can be updated', function () {
        $created = makeProductType('Moldura');

        $this->putJson("/api/product-types/{$created['id']}", ['name' => 'Moldura', 'icon' => 'fa-image'])
            ->assertJsonPath('icon', 'fa-image');
    });

    it("is exposed on the type's products", function () {
        $type = makeProductType('Caixa', icon: 'fa-box');
        $product = makeProduct('Caixa Redonda', typeId: $type['id']);

        $this->getJson("/api/products/{$product['id']}")->assertJsonPath('type.icon', 'fa-box');
    });

    it('is always resolved on a product, guessed from the name when the type has none', function () {
        $type = makeProductType('Coração');
        expect($type['icon'])->toBeNull();

        $product = makeProduct('Coração de Viana', typeId: $type['id']);

        $this->getJson("/api/products/{$product['id']}")->assertJsonPath('type.icon', 'fa-heart');
    });

    it('falls back to the default for an unrecognisable name', function () {
        $type = makeProductType('Qualquer coisa');
        $product = makeProduct('Uma peça', typeId: $type['id']);

        $this->getJson("/api/products/{$product['id']}")->assertJsonPath('type.icon', 'fa-gift');
    });

    it('stays unresolved on the types endpoint', function () {
        // The dashboard offers "Adivinhar pelo nome" only while null still means null.
        $created = makeProductType('Coração');

        $this->getJson("/api/product-types/{$created['id']}")->assertJsonPath('icon', null);
    });
});

describe('guessing an icon', function () {
    it('lets an explicit icon win', function () {
        expect(TypeIcons::for('fa-star', 'Caixa'))->toBe('fa-star');
    });

    it('guesses from the name', function () {
        expect(TypeIcons::for(null, 'Coração de Viana'))->toBe('fa-heart')
            ->and(TypeIcons::for(null, 'Moldura pequena'))->toBe('fa-image')
            ->and(TypeIcons::for(null, 'Caixa'))->toBe('fa-box');
    });

    it('ignores accents and case', function () {
        expect(TypeIcons::for(null, 'CORACAO'))->toBe('fa-heart');
    });

    it('gives an unknown name the default', function () {
        expect(TypeIcons::for(null, 'Qualquer coisa'))->toBe('fa-gift');
    });

    it('gives a missing type the default', function () {
        expect(TypeIcons::for(null, null))->toBe('fa-gift');
    });
});

// A family nobody has photographed gets its name and an honest line on the
// landing page, not an icon in a blue disc.
describe('a family with no photograph', function () {
    it('shows its name and says so', function () {
        makeProductType('Moldura', icon: 'fa-image');

        $this->get('/')->assertSee('fotografia a caminho')->assertSee('Moldura');
    });

    it('gets no icon disc in place of a photograph', function () {
        makeProductType('Coração de Viana');

        $this->get('/')->assertDontSee('type-card-icon', false)->assertDontSee('fa-heart', false);
    });
});

describe('the placeholder module', function () {
    it('is imported by everything that draws a tile', function (string $path) {
        expect(file_get_contents(base_path($path)))->toContain('import { ProductPlaceholder }');
    })->with([
        'public/static/js/store/catalogue/cards.js',
        'public/static/js/store/gallery.js',
        'public/static/js/dashboard/products/fetch.js',
    ]);

    it('is no longer a script tag', function (string $page) {
        // Loaded for its side effect, it would hide a missing import.
        $this->get($page)->assertDontSee('js/store/placeholder.js', false);
    })->with(['/products', '/dashboard/products']);
});

it('keeps the load-bearing rules of the tile', function () {
    // Without these the icon sits top-left, or the circle's cqw width resolves
    // against the viewport. A comment-stripping regex deleted this block once.
    $css = file_get_contents(base_path('public/static/css/theme.css'));
    $block = explode('}', explode('.product-placeholder {', $css)[1])[0];

    expect($block)->toContain('display: flex')
        ->toContain('align-items: center')
        ->toContain('justify-content: center')
        ->toContain('container-type: inline-size');
});

it('styles the tile where both halves of the product load it', function () {
    // The dashboard draws this tile too, and does not load store.css.
    $this->get('/dashboard/products')->assertDontSee('css/store.css', false);

    $store = file_get_contents(base_path('public/static/css/store.css'));
    expect($store)->not->toMatch('/^\.product-placeholder \{/m')
        ->not->toMatch('/^\.product-placeholder-circle \{/m');
});
