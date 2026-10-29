<?php

/*
 * Editing a collection in a real browser. PUT replaces the row, so a form that
 * does not send image_url clears a cover the owner never touched — and the cover
 * is the collection's whole presence on the catalogue's front page.
 */

beforeEach(function () {
    signIn();
    $collection = makeCollection('Filigrana', 'Volutas e corações');

    $this->collection = $this->post("/api/collections/{$collection['id']}/cover", ['file' => photo('capa.jpg')])
        ->assertCreated()->json();
    expect($this->collection['image_url'])->not->toBeNull();
});

function editFirstCollection(string $name)
{
    $page = visit('/dashboard/collections')->resize(1280, 950);
    $page->click('#collection-rows tr[data-collection-id]');
    $page->fill('#editCollectionModal input#cof-name', $name);
    $page->click('#editCollectionModal [data-dialog-submit]');
    $page->assertMissing('#editCollectionModal.show');

    return $page;
}

it('keeps the cover through an edit', function () {
    $page = editFirstCollection('Filigrana de Viana');

    $after = $this->getJson('/api/collections/')->json('collections.0');
    expect($after['name'])->toBe('Filigrana de Viana')
        ->and($after['image_url'])->toBe($this->collection['image_url']);
    $page->assertNoJavaScriptErrors();
});

it('still shows the cover in the row afterwards', function () {
    $page = editFirstCollection('Outro nome');

    $page->assertCount('#collection-rows .dash-thumb', 1)
        ->assertDontSeeIn('#collection-rows', 'Sem capa');
});
