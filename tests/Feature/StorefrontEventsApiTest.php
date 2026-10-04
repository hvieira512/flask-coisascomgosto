<?php

/*
 * POST /api/storefront-events, the one public write outside /auth. Mostly about
 * what it refuses and what it quietly ignores: a counter that puts an error in a
 * shopper's console is worse than one that missed an event. Nobody signs in
 * here, so the catalogue is built with the models.
 */

use App\Http\Controllers\Api\StorefrontEventController;
use App\Models\ColorSet;
use App\Models\Product;
use App\Models\ProductType;
use App\Models\ProductVariant;
use App\Models\Size;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\RateLimiter;

const STOREFRONT_EVENTS_URL = '/api/storefront-events';

function storefrontEventsPiece(string $name = 'Caixa Redonda', string $setName = 'Preto e Dourado'): array
{
    $type = ProductType::firstOrCreate(['name' => 'Tipo de teste']);
    $product = Product::create(['type_id' => $type->id, 'name' => $name, 'description' => '']);
    $variant = ProductVariant::create(['product_id' => $product->id, 'color_set_id' => ColorSet::create(['name' => $setName])->id]);

    return ['product' => $product->id, 'variant' => $variant->id];
}

function storefrontEventsSend(array $body)
{
    return test()->postJson(STOREFRONT_EVENTS_URL, $body, ['X-Requested-With' => 'fetch']);
}

function storefrontEventsRows(): array
{
    return DB::table('storefront_events')->orderBy('id')->get()->map(fn ($row) => (array) $row)->all();
}

describe('it needs no account', function () {
    it('records a view from an anonymous visitor', function () {
        $response = storefrontEventsSend(['kind' => 'view', 'product_id' => storefrontEventsPiece()['product']]);

        $response->assertNoContent();
        expect($response->getContent())->toBe('');
    });

    // A crawler cannot set a header outside the CORS safelist, and a cross-site
    // form cannot set one at all.
    it('requires the header', function () {
        $this->postJson(STOREFRONT_EVENTS_URL, ['kind' => 'view', 'product_id' => storefrontEventsPiece()['product']])
            ->assertForbidden();
    });
});

describe('what it refuses', function () {
    it('refuses an unknown kind with 400', function () {
        storefrontEventsSend(['kind' => 'clique'])->assertStatus(400);
    });

    // So whoever mistyped it can see the kinds without reading the source.
    it('names the kinds it takes', function () {
        expect(storefrontEventsSend(['kind' => 'clique'])->getContent())->toContain('view')->toContain('enquiry');
    });

    it('refuses a missing kind with 400', function () {
        storefrontEventsSend(['product_id' => 1])->assertStatus(400);
    });
});

describe('what it quietly ignores', function () {
    // Deleted between the page loading and this arriving: nothing to count.
    it('records nothing for an invented piece', function () {
        storefrontEventsSend(['kind' => 'view', 'product_id' => 9999])->assertNoContent();

        expect(storefrontEventsRows())->toBe([]);
    });

    // Losing the whole event would hide a client bug twice over.
    it("drops another piece's colour but keeps the enquiry", function () {
        $piece = storefrontEventsPiece();
        $other = storefrontEventsPiece('Outra peça', 'Branco e Azul');

        storefrontEventsSend(['kind' => 'enquiry', 'product_id' => $piece['product'], 'variant_id' => $other['variant']]);

        $rows = storefrontEventsRows();
        expect($rows)->toHaveCount(1)
            ->and($rows[0]['kind'])->toBe('enquiry')
            ->and($rows[0]['product_id'])->toBe($piece['product'])
            ->and($rows[0]['variant_id'])->toBeNull();
    });

    it('drops a colour with no piece', function () {
        storefrontEventsSend(['kind' => 'enquiry', 'variant_id' => storefrontEventsPiece()['variant']]);

        $rows = storefrontEventsRows();
        expect($rows)->toHaveCount(1)->and($rows[0]['variant_id'])->toBeNull();
    });

    it('drops an invented size', function () {
        storefrontEventsSend(['kind' => 'enquiry', 'product_id' => storefrontEventsPiece()['product'], 'size_id' => 9999]);

        $rows = storefrontEventsRows();
        expect($rows)->toHaveCount(1)
            ->and($rows[0]['kind'])->toBe('enquiry')
            ->and($rows[0]['size_id'])->toBeNull();
    });
});

describe('what each kind stores', function () {
    // Not which page, not where from: anything more would be about a person.
    it('stores nothing at all for a visit', function () {
        storefrontEventsSend(['kind' => 'visit']);

        $rows = storefrontEventsRows();
        expect($rows)->toHaveCount(1)->and($rows[0]['kind'])->toBe('visit');
        foreach (['product_id', 'variant_id', 'size_id', 'facet', 'facet_label', 'term', 'results'] as $column) {
            expect($rows[0][$column])->toBeNull();
        }
    });

    it('stores the colour and size of an enquiry', function () {
        $piece = storefrontEventsPiece();
        $size = Size::orderBy('position')->first();

        storefrontEventsSend(['kind' => 'enquiry', 'product_id' => $piece['product'], 'variant_id' => $piece['variant'], 'size_id' => $size->id]);

        $rows = storefrontEventsRows();
        expect($rows[0]['variant_id'])->toBe($piece['variant'])->and($rows[0]['size_id'])->toBe($size->id);
    });

    it('stores the normalised term and result count of a search', function () {
        storefrontEventsSend(['kind' => 'search', 'term' => '  Caixa   AZUL ', 'results' => 0]);

        $rows = storefrontEventsRows();
        expect($rows[0]['term'])->toBe('caixa azul')->and($rows[0]['results'])->toBe(0);
    });

    it('stores the facet and label of a filter', function () {
        storefrontEventsSend(['kind' => 'filter', 'facet' => 'Tipo', 'facet_label' => 'Caixa']);

        $rows = storefrontEventsRows();
        expect([$rows[0]['facet'], $rows[0]['facet_label']])->toBe(['Tipo', 'Caixa']);
    });
});

// A real shopper sends one view and maybe an enquiry; the limit costs them nothing.
describe('the flood', function () {
    it('refuses the event after the allowance', function () {
        $body = ['kind' => 'view', 'product_id' => storefrontEventsPiece()['product']];
        foreach (range(1, StorefrontEventController::PER_MINUTE) as $_) {
            storefrontEventsSend($body)->assertNoContent();
        }

        storefrontEventsSend($body)->assertStatus(429);
    });

    // Otherwise somebody who keeps knocking keeps the window full.
    it('does not count the refusals', function () {
        $body = ['kind' => 'view', 'product_id' => storefrontEventsPiece()['product']];
        foreach (range(1, StorefrontEventController::PER_MINUTE + 5) as $_) {
            storefrontEventsSend($body);
        }

        expect(RateLimiter::attempts('storefront-events:127.0.0.1'))->toBe(StorefrontEventController::PER_MINUTE);
    });

    it('drains on its own', function () {
        $body = ['kind' => 'view', 'product_id' => storefrontEventsPiece()['product']];
        foreach (range(1, StorefrontEventController::PER_MINUTE) as $_) {
            storefrontEventsSend($body);
        }
        storefrontEventsSend($body)->assertStatus(429);

        $this->travel(61)->seconds();

        storefrontEventsSend($body)->assertNoContent();
    });

    it('does not record a refused event', function () {
        $body = ['kind' => 'view', 'product_id' => storefrontEventsPiece()['product']];
        foreach (range(1, StorefrontEventController::PER_MINUTE + 3) as $_) {
            storefrontEventsSend($body);
        }

        expect(storefrontEventsRows())->toHaveCount(StorefrontEventController::PER_MINUTE);
    });
});

describe('the swagger document', function () {
    // No padlock: a shopper has no token.
    it('documents the endpoint as public, and its 429', function () {
        $post = $this->getJson('/api/swagger.json')->json('paths./storefront-events.post');

        expect($post['security'] ?? [])->toBe([])
            ->and($post['responses'])->toHaveKey('429');
    });
});
