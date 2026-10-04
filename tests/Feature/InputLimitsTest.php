<?php

/*
 * Text longer than its column used to reach MySQL, which refused it, and the
 * caller got a 500. Every such field is now checked first, and answered 400.
 */

beforeEach(fn () => signIn());

it('refuses text longer than its column with 400', function (string $uri, array $payload) {
    $this->postJson($uri, $payload)->assertStatus(400)->assertJsonPath('message', 'Input payload validation failed');
})->with([
    'material name' => ['/api/materials/', ['name' => str_repeat('a', 101)]],
    'colour name' => ['/api/colors/', ['name' => str_repeat('a', 81)]],
    'colour hex' => ['/api/colors/', ['name' => 'Azul', 'hex' => '#1234567890']],
    'size name' => ['/api/sizes/', ['name' => str_repeat('a', 41)]],
    'collection name' => ['/api/collections/', ['name' => str_repeat('a', 121)]],
    'type icon' => ['/api/product-types/', ['name' => 'Caixa', 'icon' => str_repeat('a', 61)]],
    'colour set name' => ['/api/color-sets/', ['name' => str_repeat('a', 121), 'color_ids' => []]],
    'event location' => ['/api/events/', ['name' => 'Feira', 'starts_on' => '2026-01-01', 'location' => str_repeat('a', 181)]],
    'account e-mail' => ['/api/auth/register', ['username' => 'bea', 'email' => str_repeat('a', 180).'@example.com', 'password' => 'x']],
]);

it('refuses a product name longer than its column', function () {
    $this->postJson('/api/products/', ['name' => str_repeat('a', 181), 'description' => '', 'type_id' => productType()['id']])
        ->assertStatus(400);
});

it('refuses a contact field longer than its column', function () {
    $this->putJson('/api/contacts/', ['whatsapp' => str_repeat('9', 41)])->assertStatus(400);
});

it('refuses an event date that is not one', function (string $field) {
    $this->postJson('/api/events/', ['name' => 'Feira', 'starts_on' => '2026-01-01', $field => '30 de Fevereiro'])
        ->assertStatus(400);
})->with(['starts_on', 'ends_on']);

// Public, so anyone could have filled the error log through it.
it('refuses an over-long facet from a visitor with 400', function () {
    $this->app['auth']->forgetGuards();

    $this->withHeader('X-Requested-With', 'fetch')
        ->postJson('/api/storefront-events', ['kind' => 'filter', 'facet' => str_repeat('f', 21), 'facet_label' => 'Caixa'])
        ->assertStatus(400);
});

it('refuses an over-long alt text on an upload', function () {
    $product = makeProduct();
    $variant = makeVariant($product);

    $this->post("/api/products/{$product['id']}/images/upload", ['file' => photo(), 'variant_id' => $variant['id'], 'alt' => str_repeat('a', 256)])
        ->assertStatus(400);
});
