<?php

/*
 * The storefront event log itself: that each kind stores what it should, that
 * the foreign keys behave as the schema claims, and, the one that matters most,
 * that the table has no column capable of holding anything about a person.
 */

use App\Models\ColorSet;
use App\Models\Product;
use App\Models\ProductType;
use App\Models\ProductVariant;
use App\Models\StorefrontEvent;
use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

function analyticsRepositoryPiece(): array
{
    $type = ProductType::create(['name' => 'Caixa']);
    $product = Product::create(['type_id' => $type->id, 'name' => 'Caixa Redonda', 'description' => '']);
    $variant = ProductVariant::create(['product_id' => $product->id, 'color_set_id' => ColorSet::create(['name' => 'Preto e Dourado'])->id]);

    return ['product_id' => $product->id, 'variant_id' => $variant->id];
}

function analyticsRepositoryRecord(array $body): void
{
    test()->postJson('/api/storefront-events', $body, ['X-Requested-With' => 'fetch'])->assertNoContent();
}

function analyticsRepositoryRows(): array
{
    return DB::table('storefront_events')->orderBy('id')->get()->map(fn ($row) => (array) $row)->all();
}

// A comment in the migration cannot enforce "no identifiers", and the next
// person to add a column will not have read it.
describe('the privacy promise is in the schema', function () {
    it('has no column that could hold an identifier', function () {
        expect(Schema::getColumnListing('storefront_events'))->toEqualCanonicalizing([
            'id', 'kind', 'product_id', 'variant_id', 'size_id',
            'facet', 'facet_label', 'term', 'results', 'created_at',
        ]);
    });

    it('lacks the obvious names', function (string $forbidden) {
        expect(Schema::hasColumn('storefront_events', $forbidden))->toBeFalse();
    })->with(['ip', 'ip_address', 'user_agent', 'session', 'session_id', 'visitor', 'visitor_id', 'fingerprint', 'email', 'referrer']);
});

describe('recording each kind', function () {
    it('stores the piece of a view and nothing else', function () {
        $piece = analyticsRepositoryPiece();

        analyticsRepositoryRecord(['kind' => 'view', 'product_id' => $piece['product_id']]);

        [$row] = analyticsRepositoryRows();
        expect($row['kind'])->toBe('view')
            ->and($row['product_id'])->toBe($piece['product_id'])
            ->and([$row['variant_id'], $row['term'], $row['facet']])->toBe([null, null, null])
            ->and($row['created_at'])->not->toBeNull();
    });

    // A label is a name the owners gave something: "filigrana" would read as a typo.
    it('trims a filter label but keeps its case', function () {
        analyticsRepositoryRecord(['kind' => 'filter', 'facet' => 'Tipo', 'facet_label' => '  Caixa  ']);

        [$row] = analyticsRepositoryRows();
        expect([$row['facet'], $row['facet_label']])->toBe(['Tipo', 'Caixa']);
    });

    it('accepts every declared kind', function (string $kind) {
        analyticsRepositoryRecord(['kind' => $kind]);

        expect(analyticsRepositoryRows())->toHaveCount(1);
    })->with(StorefrontEvent::KINDS);
});

// Two spellings of one search would split its count.
describe('the search term', function () {
    it('collapses case and whitespace', function (string $raw, string $expected) {
        analyticsRepositoryRecord(['kind' => 'search', 'term' => $raw, 'results' => 1]);

        expect(analyticsRepositoryRows()[0]['term'])->toBe($expected);
    })->with([
        ['Caixa', 'caixa'],
        ['  caixa   redonda  ', 'caixa redonda'],
        ["CAIXA\tDE\nJOIAS", 'caixa de joias'],
    ]);

    it('cannot overflow the column', function () {
        analyticsRepositoryRecord(['kind' => 'search', 'term' => str_repeat('a', 400), 'results' => 1]);

        expect(analyticsRepositoryRows()[0]['term'])->toHaveLength(120);
    });
});

describe('when the catalogue changes', function () {
    // A view count for a piece that no longer exists answers nothing.
    it('takes the history with a deleted piece', function () {
        $piece = analyticsRepositoryPiece();
        analyticsRepositoryRecord(['kind' => 'view', 'product_id' => $piece['product_id']]);

        DB::table('products')->where('id', $piece['product_id'])->delete();

        expect(analyticsRepositoryRows())->toBe([]);
    });

    // The question was asked, and it still counts for the piece.
    it('keeps the enquiry when its colour is deleted', function () {
        $piece = analyticsRepositoryPiece();
        analyticsRepositoryRecord(['kind' => 'enquiry', 'product_id' => $piece['product_id'], 'variant_id' => $piece['variant_id']]);

        DB::table('product_variants')->where('id', $piece['variant_id'])->delete();

        [$row] = analyticsRepositoryRows();
        expect($row['product_id'])->toBe($piece['product_id'])->and($row['variant_id'])->toBeNull();
    });

    it('has the database refuse an invented piece', function () {
        DB::table('storefront_events')->insert(['kind' => 'view', 'product_id' => 9999]);
    })->throws(QueryException::class);
});

describe('when counting started', function () {
    it('is unknown before anything happens', function () {
        expect(StorefrontEvent::overview(7)['window']['counting_since'])->toBeNull();
    });

    it('is the first event', function () {
        $piece = analyticsRepositoryPiece();
        analyticsRepositoryRecord(['kind' => 'view', 'product_id' => $piece['product_id']]);
        analyticsRepositoryRecord(['kind' => 'view', 'product_id' => $piece['product_id']]);

        expect(StorefrontEvent::overview(7)['window']['counting_since'])->not->toBeNull();
    });
});

/*
 * Every piece that predates dating carries the date the column arrived, so the
 * count is honest only over a window that begins after the earliest dated piece;
 * before it the whole back catalogue would read as this week's work.
 */
describe('pieces added', function () {
    it('says nothing while the window predates the earliest piece', function () {
        analyticsRepositoryPiece();
        DB::table('products')->update(['created_at' => DB::raw('NOW() - INTERVAL 3 DAY')]);

        expect(StorefrontEvent::piecesAdded(7))->toBeNull();
    });

    it('counts once the window starts after the earliest piece', function () {
        $old = analyticsRepositoryPiece();
        DB::table('products')->where('id', $old['product_id'])->update(['created_at' => DB::raw('NOW() - INTERVAL 60 DAY')]);
        Product::create(['type_id' => ProductType::first()->id, 'name' => 'Caixa nova', 'description' => '']);

        expect(StorefrontEvent::piecesAdded(7))->toBe(1);
    });

    it('does not call a piece older than the window new', function () {
        $old = analyticsRepositoryPiece();
        DB::table('products')->where('id', $old['product_id'])->update(['created_at' => DB::raw('NOW() - INTERVAL 60 DAY')]);
        $recent = Product::create(['type_id' => ProductType::first()->id, 'name' => 'Caixa de ontem', 'description' => '']);
        DB::table('products')->where('id', $recent->id)->update(['created_at' => DB::raw('NOW() - INTERVAL 30 DAY')]);

        expect(StorefrontEvent::piecesAdded(7))->toBe(0)
            ->and(StorefrontEvent::piecesAdded(40))->toBe(1);
    });
});
