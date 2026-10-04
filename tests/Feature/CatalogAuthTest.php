<?php

// Catalogue writes need a bearer token or the dashboard's session; reads stay
// public. Payloads are valid on purpose, so a 401 cannot come from validation.

it('refuses an anonymous write with 401', function (string $method, string $path, ?array $payload) {
    $this->json($method, $path, $payload ?? [])->assertUnauthorized();
})->with([
    ['POST', '/api/materials/', ['name' => 'Intruso']],
    ['PUT', '/api/materials/1', ['name' => 'Intruso']],
    ['DELETE', '/api/materials/1', null],
    ['POST', '/api/products/', ['name' => 'Intruso', 'description' => 'x', 'type_id' => 1]],
    ['PUT', '/api/products/1', ['name' => 'Intruso', 'description' => 'x', 'type_id' => 1]],
    ['DELETE', '/api/products/1', null],
    ['POST', '/api/colors/', ['name' => 'Intruso']],
    ['DELETE', '/api/colors/1', null],
    ['POST', '/api/collections/', ['name' => 'Intruso']],
    ['DELETE', '/api/collections/1', null],
    ['POST', '/api/product-types/', ['name' => 'Intruso']],
    ['DELETE', '/api/product-types/1', null],
    ['POST', '/api/color-sets/', ['name' => 'Intruso', 'color_ids' => [1]]],
    ['DELETE', '/api/color-sets/1', null],
    ['POST', '/api/sizes/', ['name' => 'XL']],
    ['DELETE', '/api/sizes/1', null],
    ['POST', '/api/products/1/variants', ['color_set_id' => 1]],
    ['DELETE', '/api/products/1/variants/1', null],
    ['POST', '/api/products/1/images', ['url' => '/x.jpg', 'variant_id' => 1]],
    ['DELETE', '/api/products/1/images/1', null],
    ['PUT', '/api/products/1/sizes', ['size_ids' => []]],
]);

// The storefront is anonymous, so every list stays readable.
it('keeps reads public', function (string $path) {
    $this->getJson($path)->assertOk();
})->with([
    '/api/products/', '/api/materials/', '/api/colors/', '/api/collections/',
    '/api/product-types/', '/api/color-sets/', '/api/sizes/',
]);

it('writes nothing without a token', function () {
    $this->postJson('/api/materials/', ['name' => 'Intruso']);

    expect($this->getJson('/api/materials/')->json('materials.*.name'))->not->toContain('Intruso');
});

it('still lets a signed-in write through', function () {
    signIn();

    $this->postJson('/api/materials/', ['name' => 'Madeira'])->assertCreated();
});
