<?php

/*
 * Every photograph belongs to one of the product's colour sets. It used to be
 * able to belong to the product as a whole, standing in for any colour that had
 * none — which showed a shopper who picked Preto e Branco a photograph of the
 * white-and-gold piece. So variant_id is required, at every entry point.
 */

beforeEach(fn () => signIn());

/** A product with one colour, which is the least a photograph needs. */
function imagesPiece(): array
{
    $set = makeColorSet('White and Green', [makeColor('White')['id'], makeColor('Green')['id']]);
    $product = makeProduct('Caixa Redonda');

    return ['product' => $product, 'variant' => makeVariant($product, $set)];
}

function imagesAdd(array $piece, string $url, array $extra = []): \Illuminate\Testing\TestResponse
{
    return test()->postJson("/api/products/{$piece['product']['id']}/images", [
        'url' => $url, 'variant_id' => $piece['variant']['id'], ...$extra,
    ]);
}

describe('a photograph belongs to a colour', function () {
    it('gives a product with no photographs no tile', function () {
        $product = makeProduct('Caixa');

        $body = $this->getJson("/api/products/{$product['id']}")->json();

        // Gone from the payload too: a client reading product["images"] should
        // fail rather than see [].
        expect($body['primary_image'])->toBeNull()->and($body)->not->toHaveKey('images');
    });

    it('returns the photograph with its colour', function () {
        $piece = imagesPiece();

        imagesAdd($piece, '/static/img/caixa.jpg', ['alt' => 'Caixa redonda'])
            ->assertCreated()
            ->assertJsonPath('url', '/static/img/caixa.jpg')
            ->assertJsonPath('variant_id', $piece['variant']['id']);
    });

    it('refuses one without a colour', function () {
        $piece = imagesPiece();

        $this->postJson("/api/products/{$piece['product']['id']}/images", ['url' => '/static/img/caixa.jpg'])->assertStatus(400);
    });

    it('refuses a colour of another product with 404', function () {
        $piece = imagesPiece();
        $other = makeProduct('Outra peça');

        $this->postJson("/api/products/{$other['id']}/images", ['url' => '/x.jpg', 'variant_id' => $piece['variant']['id']])->assertNotFound();
    });

    it('refuses a missing url with 400', function () {
        $piece = imagesPiece();

        $this->postJson("/api/products/{$piece['product']['id']}/images", ['variant_id' => $piece['variant']['id']])->assertStatus(400);
    });

    it('answers 404 for an unknown product', function () {
        $this->getJson('/api/products/9999/images')->assertNotFound();
        $this->postJson('/api/products/9999/images', ['url' => '/x.jpg', 'variant_id' => 1])->assertNotFound();
    });
});

describe('listing them', function () {
    it('lists them in position order', function () {
        $piece = imagesPiece();
        foreach ([['/c.jpg', 3], ['/a.jpg', 1], ['/b.jpg', 2]] as [$url, $position]) {
            imagesAdd($piece, $url, ['position' => $position]);
        }

        expect($this->getJson("/api/products/{$piece['product']['id']}/images")->json('*.url'))->toBe(['/a.jpg', '/b.jpg', '/c.jpg']);
    });

    it('shows them on their colour', function () {
        $piece = imagesPiece();
        imagesAdd($piece, '/white-green.jpg');

        expect($this->getJson("/api/products/{$piece['product']['id']}")->json('variants.0.images.*.url'))->toBe(['/white-green.jpg']);
    });

    it('narrows the list to one colour', function () {
        $piece = imagesPiece();
        imagesAdd($piece, '/white-green.jpg');
        $other = makeVariant($piece['product'], makeColorSet('Preto e Dourado', [makeColor('Preto')['id']]));
        $this->postJson("/api/products/{$piece['product']['id']}/images", ['url' => '/black-gold.jpg', 'variant_id' => $other['id']]);

        expect($this->getJson("/api/products/{$piece['product']['id']}/images?variant_id={$other['id']}")->json('*.url'))->toBe(['/black-gold.jpg']);
    });
});

describe('the tile the catalogue shows', function () {
    // A piece whose first colour has no photograph still gets a tile from
    // whichever colour does, not a placeholder.
    it('is the first photograph of the first photographed colour', function () {
        $piece = imagesPiece();
        makeVariant($piece['product'], makeColorSet('Sem fotografia', [makeColor('Cinza')['id']]));
        imagesAdd($piece, '/first.jpg', ['position' => 1]);
        imagesAdd($piece, '/second.jpg', ['position' => 2]);

        $this->getJson("/api/products/{$piece['product']['id']}")->assertJsonPath('primary_image.url', '/first.jpg');
    });
});

describe('changing and removing', function () {
    it('keeps the colour requirement on update', function () {
        $piece = imagesPiece();
        $made = imagesAdd($piece, '/old.jpg')->json();

        $this->putJson("/api/products/{$piece['product']['id']}/images/{$made['id']}", ['url' => '/new.jpg', 'alt' => 'novo'])->assertStatus(400);
    });

    it('changes the url', function () {
        $piece = imagesPiece();
        $made = imagesAdd($piece, '/old.jpg')->json();

        $this->putJson("/api/products/{$piece['product']['id']}/images/{$made['id']}", [
            'url' => '/new.jpg', 'alt' => 'novo', 'variant_id' => $piece['variant']['id'],
        ])->assertOk()->assertJsonPath('url', '/new.jpg');
    });

    it('deletes it', function () {
        $piece = imagesPiece();
        $made = imagesAdd($piece, '/x.jpg')->json();

        $this->deleteJson("/api/products/{$piece['product']['id']}/images/{$made['id']}")->assertOk();
        $this->getJson("/api/products/{$piece['product']['id']}/images")->assertExactJson([]);
    });

    it('keeps another product\'s photograph out of reach', function () {
        $piece = imagesPiece();
        $second = makeProduct('Segunda');
        $image = imagesAdd($piece, '/x.jpg')->json();

        $this->deleteJson("/api/products/{$second['id']}/images/{$image['id']}")->assertNotFound();
    });

    it('removes the photographs with the product', function () {
        $piece = imagesPiece();
        imagesAdd($piece, '/x.jpg');

        $this->deleteJson("/api/products/{$piece['product']['id']}");

        $this->getJson("/api/products/{$piece['product']['id']}/images")->assertNotFound();
    });

    // A photograph with no colour is the state this cutover removed.
    it('removes the photographs with their colour', function () {
        $piece = imagesPiece();
        imagesAdd($piece, '/x.jpg')->assertCreated();

        $this->deleteJson("/api/products/{$piece['product']['id']}/variants/{$piece['variant']['id']}");

        $this->getJson("/api/products/{$piece['product']['id']}/images")->assertExactJson([]);
    });
});
