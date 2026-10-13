<?php

// The paging every list shares, exercised through /api/materials/.

beforeEach(fn () => signIn());

function paginationMaterials(int $count): void
{
    foreach (range(1, $count) as $i) {
        makeMaterial(sprintf('M%02d', $i));
    }
}

describe('the query string', function () {
    it('defaults to the first page of ten', function () {
        $this->getJson('/api/materials/')->assertJsonPath('pagination', ['total' => 0, 'page' => 1, 'pages' => 0, 'limit' => 10]);
    });

    it('derives the offset from page and limit', function () {
        paginationMaterials(12);

        expect($this->getJson('/api/materials/?page=3&limit=5')->json('materials.*.name'))->toBe(['M11', 'M12']);
    });

    it('clamps the limit to the maximum', function () {
        $this->getJson('/api/materials/?limit=10000')
            ->assertOk()
            ->assertJsonPath('pagination.limit', 100)
            ->assertJsonPath('pagination.page', 1);
    });

    it('refuses a page that is not an integer', function (string $value) {
        $this->getJson("/api/materials/?page={$value}")->assertStatus(400);
    })->with(['abc', '1.5', '']);

    it('refuses a page or limit below one', function (string $value) {
        $this->getJson("/api/materials/?page={$value}")->assertStatus(400);
        $this->getJson("/api/materials/?limit={$value}")->assertStatus(400);
    })->with(['0', '-1']);
});

describe('the envelope', function () {
    it('rounds the page count up', function () {
        paginationMaterials(21);

        expect($this->getJson('/api/materials/')->json('pagination.pages'))->toBe(3);
    });

    it('adds no page for an exact multiple', function () {
        paginationMaterials(20);

        expect($this->getJson('/api/materials/')->json('pagination.pages'))->toBe(2);
    });

    it('has no pages when there is nothing', function () {
        expect($this->getJson('/api/materials/')->json('pagination.pages'))->toBe(0);
    });

    it('echoes the page and limit', function () {
        paginationMaterials(5);

        expect($this->getJson('/api/materials/?page=2&limit=3')->json('pagination'))
            ->toBe(['total' => 5, 'page' => 2, 'pages' => 2, 'limit' => 3]);
    });
});
