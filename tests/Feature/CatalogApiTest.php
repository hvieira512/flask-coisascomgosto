<?php

use Illuminate\Http\UploadedFile;

beforeEach(fn () => signIn());

/** Drop the signed-in owner, so the next request is a stranger's. */
function catalogApiAnonymous(): void
{
    app('auth')->forgetGuards();
}

function catalogApiUploadDir(string $folder): string
{
    return config('uploads.root')."/static/img/{$folder}";
}

describe('collections', function () {
    it('answers an empty page on an empty table', function () {
        $body = $this->getJson('/api/collections/')->json();

        expect($body['collections'])->toBe([])->and($body['pagination']['total'])->toBe(0);
    });

    it('creates and returns the collection', function () {
        $this->postJson('/api/collections/', ['name' => 'Barra da Saia', 'description' => 'Regional'])
            ->assertCreated()
            ->assertJsonPath('name', 'Barra da Saia')
            ->assertJsonPath('description', 'Regional');
    });

    it('makes the description optional', function () {
        $this->postJson('/api/collections/', ['name' => 'Minimal'])
            ->assertCreated()
            ->assertJsonPath('description', null);
    });

    it('refuses a name already taken with 409', function () {
        makeCollection('Barra da Saia');

        $this->postJson('/api/collections/', ['name' => 'Barra da Saia'])->assertStatus(409);
    });

    it('refuses a missing name with 400', function () {
        $this->postJson('/api/collections/', [])->assertStatus(400);
    });

    it('renames', function () {
        $made = makeCollection('Barra da Saia');

        $this->putJson("/api/collections/{$made['id']}", ['name' => 'Renamed'])->assertOk()->assertJsonPath('name', 'Renamed');
    });

    it('answers 404 for an unknown id', function () {
        $this->getJson('/api/collections/9999')->assertNotFound();
        $this->putJson('/api/collections/9999', ['name' => 'X'])->assertNotFound();
        $this->deleteJson('/api/collections/9999')->assertNotFound();
    });

    it('searches by name', function () {
        makeCollection('Barra da Saia');
        makeCollection('Lenco dos Namorados');

        expect($this->getJson('/api/collections/?q=Barra')->json('collections.*.name'))->toBe(['Barra da Saia']);
    });

    // The colour set the piece is offered in is unlinked, not deleted.
    it('leaves its pieces and their colourways when deleted', function () {
        $collection = makeCollection('Barra da Saia');
        $product = makeProduct('Caixa');
        putInCollection($product, $collection);

        $this->deleteJson("/api/collections/{$collection['id']}");

        $body = $this->getJson("/api/products/{$product['id']}")->json();
        expect($body['collections'])->toBe([])->and($body['variants'])->toHaveCount(1);
    });
});

// A link, not a move: a set may be gathered by several collections at once.
describe('the colour sets a collection gathers', function () {
    beforeEach(function () {
        $white = makeColor('Branco', '#FFFFFF');
        $this->sets = [
            'gold' => makeColorSet('Branco e Dourado', [$white['id']]),
            'black' => makeColorSet('Preto e Branco', [$white['id']]),
            'blue' => makeColorSet('Azul e Branco', [$white['id']]),
        ];
        $this->gather = fn (int $collectionId, array $ids) => $this->putJson("/api/collections/{$collectionId}/color-sets", ['color_set_ids' => $ids]);
        $this->gathered = fn (int $collectionId) => $this->getJson("/api/collections/{$collectionId}/color-sets")->json('*.name');
    });

    it('starts with none', function () {
        $collection = makeCollection('Filigrana');

        $this->getJson("/api/collections/{$collection['id']}/color-sets")->assertExactJson([]);
    });

    it('can be assigned', function () {
        $collection = makeCollection('Filigrana');

        $response = ($this->gather)($collection['id'], [$this->sets['gold']['id'], $this->sets['black']['id']])->assertOk();
        expect(collect($response->json('*.name'))->sort()->values()->all())->toBe(['Branco e Dourado', 'Preto e Branco']);
    });

    it('names the collection on the colour set', function () {
        $collection = makeCollection('Filigrana');
        ($this->gather)($collection['id'], [$this->sets['gold']['id']]);

        expect($this->getJson("/api/color-sets/{$this->sets['gold']['id']}")->json('collections.*.name'))->toBe(['Filigrana']);
    });

    it('takes out the one left out, without deleting it', function () {
        $collection = makeCollection('Filigrana');
        ($this->gather)($collection['id'], [$this->sets['gold']['id'], $this->sets['black']['id']]);
        ($this->gather)($collection['id'], [$this->sets['gold']['id']]);

        expect(($this->gathered)($collection['id']))->toBe(['Branco e Dourado'])
            ->and($this->getJson("/api/color-sets/{$this->sets['black']['id']}")->json('collections'))->toBe([]);
    });

    it('is emptied by an empty list', function () {
        $collection = makeCollection('Filigrana');
        ($this->gather)($collection['id'], [$this->sets['gold']['id']]);

        expect(($this->gather)($collection['id'], [])->json())->toBe([]);
    });

    // The whole point of the join: "Branco e Dourado" is Filigrana's and
    // Bordados', without being created twice.
    it('keeps a set another collection has in both', function () {
        $bordados = makeCollection('Bordados');
        $filigrana = makeCollection('Filigrana');
        ($this->gather)($bordados['id'], [$this->sets['gold']['id']]);

        ($this->gather)($filigrana['id'], [$this->sets['gold']['id']]);

        expect(($this->gathered)($bordados['id']))->toBe(['Branco e Dourado'])
            ->and(($this->gathered)($filigrana['id']))->toBe(['Branco e Dourado'])
            ->and(collect($this->getJson("/api/color-sets/{$this->sets['gold']['id']}")->json('collections.*.name'))->sort()->values()->all())
            ->toBe(['Bordados', 'Filigrana']);
    });

    it('does not disturb the other collections', function () {
        $bordados = makeCollection('Bordados');
        $filigrana = makeCollection('Filigrana');
        ($this->gather)($bordados['id'], [$this->sets['black']['id']]);

        ($this->gather)($filigrana['id'], [$this->sets['gold']['id']]);

        expect(($this->gathered)($bordados['id']))->toBe(['Preto e Branco']);
    });

    it('answers 404 for an unknown colour set and changes nothing', function () {
        $collection = makeCollection('Filigrana');
        ($this->gather)($collection['id'], [$this->sets['gold']['id']]);

        ($this->gather)($collection['id'], [9999])->assertNotFound();
        expect(($this->gathered)($collection['id']))->toBe(['Branco e Dourado']);
    });

    it('answers 404 for an unknown collection', function () {
        ($this->gather)(9999, [$this->sets['gold']['id']])->assertNotFound();
        $this->getJson('/api/collections/9999/color-sets')->assertNotFound();
    });

    it('needs a token to change', function () {
        $collection = makeCollection('Filigrana');
        catalogApiAnonymous();

        ($this->gather)($collection['id'], [$this->sets['gold']['id']])->assertUnauthorized();
    });

    // The storefront reads collections without signing in.
    it('does not need one to read', function () {
        $collection = makeCollection('Filigrana');
        catalogApiAnonymous();

        $this->getJson("/api/collections/{$collection['id']}/color-sets")->assertOk();
    });
});

// Chosen rather than derived from the pieces: which photograph speaks for a
// collection is an editorial decision.
describe('a collection cover', function () {
    beforeEach(function () {
        $this->upload = fn (int $collectionId, string $name = 'capa.jpg') => $this->post("/api/collections/{$collectionId}/cover", ['file' => photo($name)]);
        $this->stored = fn (string $url) => is_file(catalogApiUploadDir('collections').'/'.basename($url));
    });

    it('is absent on a new collection', function () {
        expect(makeCollection('Filigrana')['image_url'])->toBeNull();
    });

    // A path placed by hand still works, the way product images do.
    it('can be set as a plain url', function () {
        $this->postJson('/api/collections/', ['name' => 'Filigrana', 'image_url' => '/static/img/logo.png'])
            ->assertJsonPath('image_url', '/static/img/logo.png');
    });

    it('is stored on upload and the collection points at it', function () {
        $collection = makeCollection('Filigrana');

        $url = ($this->upload)($collection['id'])->assertCreated()->json('image_url');

        expect($url)->toStartWith('/static/img/collections/')
            ->and(($this->stored)($url))->toBeTrue();
    });

    // Its own folder lets the sweep tell an unused cover from a photograph a
    // product row still points at.
    it('is not stored with the pieces', function () {
        ($this->upload)(makeCollection('Filigrana')['id']);

        expect(is_dir(catalogApiUploadDir('products')))->toBeFalse();
    });

    // Nothing in the application deletes a file; the sweep collects it once
    // nothing points at it.
    it('keeps the file it replaced', function () {
        $collection = makeCollection('Filigrana');
        $first = ($this->upload)($collection['id'])->json('image_url');
        $second = ($this->upload)($collection['id'], 'outra.jpg')->json('image_url');

        expect($first)->not->toBe($second)
            ->and(($this->stored)($first))->toBeTrue()
            ->and(($this->stored)($second))->toBeTrue();
    });

    it('keeps a piece photograph it replaced', function () {
        $piecePhoto = catalogApiUploadDir('products').'/caixa-abcd1234.jpg';
        mkdir(dirname($piecePhoto), 0775, true);
        file_put_contents($piecePhoto, 'a real photograph as far as this test cares');

        $collection = makeCollection('Filigrana');
        $this->putJson("/api/collections/{$collection['id']}", ['name' => 'Filigrana', 'image_url' => '/static/img/products/caixa-abcd1234.jpg']);
        ($this->upload)($collection['id']);

        expect(is_file($piecePhoto))->toBeTrue();
    });

    it('is cleared on removal, and the file stays', function () {
        $collection = makeCollection('Filigrana');
        $url = ($this->upload)($collection['id'])->json('image_url');

        $this->deleteJson("/api/collections/{$collection['id']}/cover")->assertOk()->assertJsonPath('image_url', null);
        expect(($this->stored)($url))->toBeTrue();
    });

    it('stays on disk when the collection is deleted', function () {
        $collection = makeCollection('Filigrana');
        $url = ($this->upload)($collection['id'])->json('image_url');

        $this->deleteJson("/api/collections/{$collection['id']}");

        expect(($this->stored)($url))->toBeTrue();
    });

    it('refuses a file that is not an image with 400', function () {
        $collection = makeCollection('Filigrana');

        $this->post("/api/collections/{$collection['id']}/cover", ['file' => UploadedFile::fake()->createWithContent('capa.jpg', "\xff\xd8\xff\xe0 nope")])
            ->assertStatus(400);
    });

    it('needs a token to upload', function () {
        $collection = makeCollection('Filigrana');
        catalogApiAnonymous();

        $this->post("/api/collections/{$collection['id']}/cover", ['file' => UploadedFile::fake()->createWithContent('capa.jpg', 'x')])
            ->assertUnauthorized();
    });

    it('answers 404 for an unknown collection', function () {
        ($this->upload)(9999)->assertNotFound();
        $this->deleteJson('/api/collections/9999/cover')->assertNotFound();
    });
});

// With no cover of its own, a collection shows a photograph of a piece it
// gathers, reached through the colour set.
describe('a borrowed cover', function () {
    beforeEach(function () {
        $this->gathered = function (string $collectionName, string $setName, string $productName, string $url) {
            $collection = makeCollection($collectionName);
            $set = makeColorSet($setName, [makeColor("{$setName} colour")['id']], [$collection['id']]);
            $product = makeProduct($productName);
            $variant = makeVariant($product, $set);
            $image = $this->postJson("/api/products/{$product['id']}/images", ['variant_id' => $variant['id'], 'url' => $url])
                ->assertCreated()->json();

            return [$collection, $set, $product, $image];
        };
        $this->cover = fn (int $id) => $this->getJson("/api/collections/{$id}")->json();
    });

    it('borrows a photograph of a piece it gathers', function () {
        [$collection] = ($this->gathered)('Filigrana', 'Branco e Dourado', 'Caixa Redonda', '/static/img/caixa.jpg');

        $body = ($this->cover)($collection['id']);
        expect($body['image_url'])->toBeNull()
            ->and($body['borrowed_image_url'])->toBe('/static/img/caixa.jpg');
    });

    it('borrows nothing when no piece is photographed', function () {
        expect(($this->cover)(makeCollection('Lenços')['id'])['borrowed_image_url'])->toBeNull();
    });

    it('does not borrow a removed photograph', function () {
        [$collection, , $product, $image] = ($this->gathered)('Filigrana', 'Branco e Dourado', 'Caixa Redonda', '/static/img/caixa.jpg');
        $this->deleteJson("/api/products/{$product['id']}/images/{$image['id']}")->assertOk();

        expect(($this->cover)($collection['id'])['borrowed_image_url'])->toBeNull();
    });

    // Why the ordering is not simply the newest piece: Filigrana and Bordados
    // both gather Branco e Dourado, which nearly every piece has, so recency
    // alone gave the two of them the same photograph side by side.
    it('prefers a colour of its own over one every collection shares', function () {
        [$filigrana, $shared] = ($this->gathered)('Filigrana', 'Branco e Dourado', 'Caixa Redonda', '/static/img/comum.jpg');
        [$bordados] = ($this->gathered)('Bordados', 'Rosa e Castanho', 'Bastidor', '/static/img/proprio.jpg');

        // The shared set's piece is the older one, so only the sharing count
        // keeps them apart.
        $this->putJson("/api/color-sets/{$shared['id']}", [
            'name' => $shared['name'],
            'color_ids' => array_column($shared['colors'], 'id'),
            'collection_ids' => [$filigrana['id'], $bordados['id']],
        ])->assertOk();

        expect(($this->cover)($bordados['id'])['borrowed_image_url'])->toBe('/static/img/proprio.jpg');
    });
});

describe('colours', function () {
    it('creates one with a hex', function () {
        $this->postJson('/api/colors/', ['name' => 'White', 'hex' => '#FFFFFF'])->assertCreated()->assertJsonPath('hex', '#FFFFFF');
    });

    it('makes the hex optional', function () {
        $this->postJson('/api/colors/', ['name' => 'Green'])->assertCreated()->assertJsonPath('hex', null);
    });

    it('refuses a name already taken with 409', function () {
        makeColor('White');

        $this->postJson('/api/colors/', ['name' => 'White'])->assertStatus(409);
    });

    it('answers 404 for an unknown id', function () {
        $this->getJson('/api/colors/9999')->assertNotFound();
    });

    it('leaves the sets it was in when deleted', function () {
        $white = makeColor('White');
        $green = makeColor('Green');
        $set = makeColorSet('White and Green', [$white['id'], $green['id']]);

        $this->deleteJson("/api/colors/{$green['id']}");

        expect($this->getJson("/api/color-sets/{$set['id']}")->json('colors.*.name'))->toBe(['White']);
    });
});

describe('colour sets', function () {
    it('keeps the colours in order', function () {
        $white = makeColor('White');
        $green = makeColor('Green');

        $response = $this->postJson('/api/color-sets/', ['name' => 'White and Green', 'color_ids' => [$white['id'], $green['id']]])->assertCreated();
        expect($response->json('colors.*.name'))->toBe(['White', 'Green']);
    });

    it('can be in no collection', function () {
        $white = makeColor('White');

        $this->postJson('/api/color-sets/', ['name' => 'Just White', 'color_ids' => [$white['id']]])
            ->assertCreated()
            ->assertJsonPath('collections', []);
    });

    it('nests its collections', function () {
        $collection = makeCollection('Barra da Saia');
        $white = makeColor('White');

        $response = $this->postJson('/api/color-sets/', ['name' => 'White', 'color_ids' => [$white['id']], 'collection_ids' => [$collection['id']]]);
        expect($response->json('collections.*.name'))->toBe(['Barra da Saia']);
    });

    it('answers 404 for an unknown colour', function () {
        $this->postJson('/api/color-sets/', ['name' => 'Ghost', 'color_ids' => [9999]])->assertNotFound();
    });

    it('answers 404 for an unknown collection', function () {
        $white = makeColor('White');

        $this->postJson('/api/color-sets/', ['name' => 'X', 'color_ids' => [$white['id']], 'collection_ids' => [9999]])->assertNotFound();
    });

    // Which is why the name is not scoped to a collection: it is one set.
    it('can be in several collections', function () {
        $first = makeCollection('First');
        $second = makeCollection('Second');
        $white = makeColor('White');

        $response = $this->postJson('/api/color-sets/', [
            'name' => 'White and Green',
            'color_ids' => [$white['id']],
            'collection_ids' => [$first['id'], $second['id']],
        ])->assertCreated();
        expect(collect($response->json('collections.*.name'))->sort()->values()->all())->toBe(['First', 'Second']);
    });

    // Two collections each with their own "White and Green" was the old shape,
    // and it made the same combination exist twice.
    it('takes the name across the whole catalogue', function () {
        $first = makeCollection('First');
        $second = makeCollection('Second');
        $white = makeColor('White');
        $payload = ['name' => 'White and Green', 'color_ids' => [$white['id']]];

        $this->postJson('/api/color-sets/', [...$payload, 'collection_ids' => [$first['id']]])->assertCreated();
        $this->postJson('/api/color-sets/', [...$payload, 'collection_ids' => [$second['id']]])->assertStatus(409);
    });

    it('replaces its colours wholesale on update', function () {
        $white = makeColor('White');
        $green = makeColor('Green');
        $red = makeColor('Red');
        $made = makeColorSet('White and Green', [$white['id'], $green['id']]);

        $response = $this->putJson("/api/color-sets/{$made['id']}", ['name' => 'Red only', 'color_ids' => [$red['id']]])->assertOk();
        expect($response->json('colors.*.name'))->toBe(['Red']);
    });

    it('collapses repeated colour ids', function () {
        $white = makeColor('White');

        $this->postJson('/api/color-sets/', ['name' => 'Doubled', 'color_ids' => [$white['id'], $white['id']]])
            ->assertCreated()
            ->assertJsonCount(1, 'colors');
    });

    it('filters by collection', function () {
        $collection = makeCollection('Barra da Saia');
        $white = makeColor('White');
        makeColorSet('Owned', [$white['id']], [$collection['id']]);
        makeColorSet('Unowned', [$white['id']]);

        $body = $this->getJson("/api/color-sets/?collection_id={$collection['id']}")->json();
        expect(array_column($body['color_sets'], 'name'))->toBe(['Owned'])
            ->and($body['pagination']['total'])->toBe(1);
    });
});

describe('sizes', function () {
    it('starts with the three the schema seeds', function () {
        expect($this->getJson('/api/sizes/')->json('sizes.*.name'))->toBe(['Pequeno', 'Médio', 'Grande']);
    });

    it('orders by position, not name', function () {
        $positions = $this->getJson('/api/sizes/')->json('sizes.*.position');
        $sorted = $positions;
        sort($sorted);

        expect($positions)->toBe($sorted);
    });

    it('creates a new one', function () {
        $this->postJson('/api/sizes/', ['name' => 'Extra grande', 'position' => 4])
            ->assertCreated()
            ->assertJsonPath('name', 'Extra grande');
    });

    it('refuses a name already taken with 409', function () {
        $this->postJson('/api/sizes/', ['name' => 'Pequeno'])->assertStatus(409);
    });

    it('round-trips an accented name', function () {
        $medium = collect($this->getJson('/api/sizes/')->json('sizes'))->firstWhere('position', 2);

        expect($medium['name'])->toBe('Médio')
            ->and($this->getJson("/api/sizes/{$medium['id']}")->json('name'))->toBe('Médio');
    });

    it('answers 404 for an unknown id', function () {
        $this->getJson('/api/sizes/9999')->assertNotFound();
    });
});

// Types are flat: the family is the type, the shape is the piece's name.
describe('product types', function () {
    it('creates one', function () {
        $this->postJson('/api/product-types/', ['name' => 'Caixa'])->assertCreated()->assertJsonPath('name', 'Caixa');
    });

    it('has no hierarchy fields', function () {
        $body = $this->getJson('/api/product-types/'.makeProductType('Caixa')['id'])->json();

        expect($body)->not->toHaveKey('parent_id')->not->toHaveKey('sub_types');
    });

    it('ignores a parent_id in the payload', function () {
        $parent = makeProductType('Caixa');

        $response = $this->postJson('/api/product-types/', ['name' => 'Caixa redonda', 'parent_id' => $parent['id']])->assertCreated();
        expect($response->json())->not->toHaveKey('parent_id');
    });

    it('refuses a name already taken with 409', function () {
        makeProductType('Caixa');

        $this->postJson('/api/product-types/', ['name' => 'Caixa'])->assertStatus(409);
    });

    it('refuses a rename onto a taken name with 409', function () {
        makeProductType('Caixa');
        $other = makeProductType('Moldura');

        $this->putJson("/api/product-types/{$other['id']}", ['name' => 'Caixa'])->assertStatus(409);
    });

    it('searches by name', function () {
        makeProductType('Caixa');
        makeProductType('Moldura');

        expect($this->getJson('/api/product-types/?q=Mold')->json('product_types.*.name'))->toBe(['Moldura']);
    });

    it('deletes', function () {
        $made = makeProductType('Caixa');

        $this->deleteJson("/api/product-types/{$made['id']}")->assertOk();
        $this->getJson("/api/product-types/{$made['id']}")->assertNotFound();
    });

    it('answers 404 for an unknown id', function () {
        $this->getJson('/api/product-types/9999')->assertNotFound();
    });

    it('refuses nonsense paging with 400', function (string $query) {
        $this->getJson("/api/product-types/{$query}")->assertStatus(400);
    })->with(['?page=abc', '?limit=0']);
});
