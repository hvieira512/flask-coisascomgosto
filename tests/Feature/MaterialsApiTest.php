<?php

beforeEach(fn () => signIn());

describe('listing', function () {
    it('answers an empty page on an empty table', function () {
        $this->getJson('/api/materials/')
            ->assertOk()
            ->assertExactJson(['materials' => [], 'pagination' => ['total' => 0, 'page' => 1, 'pages' => 0, 'limit' => 10]]);
    });

    it('lists what was created', function () {
        makeMaterial('Madeira');
        makeMaterial('Tecido');

        $body = $this->getJson('/api/materials/')->json();
        expect(array_column($body['materials'], 'name'))->toBe(['Madeira', 'Tecido'])
            ->and($body['pagination']['total'])->toBe(2);
    });

    it('searches by part of the name, and the total counts the matches', function () {
        foreach (['Madeira', 'Tecido', 'Cortiça'] as $name) {
            makeMaterial($name);
        }

        expect($this->getJson('/api/materials/?q=adei')->json('materials.*.name'))->toBe(['Madeira'])
            ->and($this->getJson('/api/materials/?q=Cort')->json('pagination.total'))->toBe(1);
    });

    it('pages', function () {
        foreach (['A', 'B', 'C'] as $name) {
            makeMaterial($name);
        }

        $body = $this->getJson('/api/materials/?page=2&limit=2')->json();
        expect(array_column($body['materials'], 'name'))->toBe(['C'])
            ->and($body['pagination'])->toBe(['total' => 3, 'page' => 2, 'pages' => 2, 'limit' => 2]);
    });

    it('answers an empty page past the end rather than an error', function () {
        makeMaterial('Madeira');

        $this->getJson('/api/materials/?page=99')->assertOk()->assertJsonPath('materials', []);
    });

    it('refuses nonsense paging with 400', function (string $query) {
        $this->getJson("/api/materials/{$query}")->assertStatus(400);
    })->with(['?page=abc', '?limit=0', '?page=0', '?limit=-1']);
});

describe('creating', function () {
    it('creates and returns the material', function () {
        $body = $this->postJson('/api/materials/', ['name' => 'Madeira'])->assertCreated()->json();

        expect($body['name'])->toBe('Madeira')->and($body['id'])->toBeInt();
    });

    it('refuses a name already taken with 409', function () {
        makeMaterial('Madeira');

        $this->postJson('/api/materials/', ['name' => 'Madeira'])->assertStatus(409);
    });

    it('refuses a missing name with 400', function () {
        $this->postJson('/api/materials/', [])->assertStatus(400);
    });
});

describe('reading one', function () {
    it('returns it', function () {
        $made = makeMaterial('Madeira');

        $this->getJson("/api/materials/{$made['id']}")->assertExactJson(['id' => $made['id'], 'name' => 'Madeira']);
    });

    it('answers 404 for an unknown id', function () {
        $this->getJson('/api/materials/9999')->assertNotFound();
    });
});

describe('updating', function () {
    it('renames, and the rename sticks', function () {
        $made = makeMaterial('Madeira');

        $this->putJson("/api/materials/{$made['id']}", ['name' => 'Madeira Frias'])->assertOk()->assertJsonPath('name', 'Madeira Frias');
        $this->getJson("/api/materials/{$made['id']}")->assertJsonPath('name', 'Madeira Frias');
    });

    it('answers 404 for an unknown id', function () {
        $this->putJson('/api/materials/9999', ['name' => 'X'])->assertNotFound();
    });

    it('refuses a name another material has with 409', function () {
        makeMaterial('Madeira');
        $other = makeMaterial('Tecido');

        $this->putJson("/api/materials/{$other['id']}", ['name' => 'Madeira'])->assertStatus(409);
    });

    it('lets a material keep its own name', function () {
        $made = makeMaterial('Madeira');

        $this->putJson("/api/materials/{$made['id']}", ['name' => 'Madeira'])->assertOk();
    });
});

describe('deleting', function () {
    it('returns what it deleted, and it is gone', function () {
        $made = makeMaterial('Madeira');

        $this->deleteJson("/api/materials/{$made['id']}")->assertOk()->assertJsonPath('name', 'Madeira');
        $this->getJson("/api/materials/{$made['id']}")->assertNotFound();
    });

    it('answers 404 for an unknown id', function () {
        $this->deleteJson('/api/materials/9999')->assertNotFound();
    });

    // A material is descriptive, not structural: a piece does not stop existing
    // because the owners tidied the material list.
    it('keeps the pieces made of it', function () {
        $material = makeMaterial('Madeira');
        $product = makeProduct('Vinho', materialIds: [$material['id']]);

        $this->deleteJson("/api/materials/{$material['id']}");

        $this->getJson("/api/products/{$product['id']}")
            ->assertJsonPath('name', 'Vinho')
            ->assertJsonPath('materials', []);
    });

    it('leaves a piece its other materials', function () {
        $wood = makeMaterial('Madeira');
        $paste = makeMaterial('Pasta de modelar');
        $product = makeProduct('Manel e Maria', materialIds: [$wood['id'], $paste['id']]);

        $this->deleteJson("/api/materials/{$paste['id']}");

        expect($this->getJson("/api/products/{$product['id']}")->json('materials.*.name'))->toBe(['Madeira']);
    });
});
