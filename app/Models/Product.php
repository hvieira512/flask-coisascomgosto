<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Collection as EloquentCollection;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Facades\DB;

/**
 * A piece. It always has a type; it may be made of several materials, declare a
 * default size, list the sizes it comes in, and be offered in several colour
 * sets. It is in a collection only through those colour sets.
 */
class Product extends Model
{
    public $timestamps = false;

    protected $fillable = ['type_id', 'default_size_id', 'name', 'description'];

    /** What a response needs, loaded in a fixed number of queries per page. */
    public const DETAIL = [
        'type',
        'defaultSize',
        'materials',
        'sizes',
        'variants.colorSet.colors',
        'variants.images',
    ];

    public function type(): BelongsTo
    {
        return $this->belongsTo(ProductType::class, 'type_id');
    }

    public function defaultSize(): BelongsTo
    {
        return $this->belongsTo(Size::class, 'default_size_id');
    }

    public function materials(): BelongsToMany
    {
        return $this->belongsToMany(Material::class, 'product_materials')->orderBy('materials.name');
    }

    public function sizes(): BelongsToMany
    {
        return $this->belongsToMany(Size::class, 'product_sizes')
            ->orderBy('sizes.position')->orderBy('sizes.id');
    }

    public function variants(): HasMany
    {
        return $this->hasMany(ProductVariant::class)->orderBy('id');
    }

    /**
     * Each id filter takes one value or several. Several read as OR — a shopper
     * ticking Caixa and Moldura wants both families — while separate filters
     * still narrow with AND. EXISTS rather than a join for collections and
     * materials, so a piece reached twice is still one row.
     */
    public function scopeFiltered(Builder $query, ?string $search, array $typeIds = [], array $collectionIds = [], array $materialIds = []): void
    {
        $term = trim((string) $search);
        if ($term !== '') {
            $query->where(fn (Builder $q) => $q
                ->where('products.name', 'like', "%{$term}%")
                ->orWhereHas('type', fn (Builder $t) => $t->where('name', 'like', "%{$term}%")));
        }

        if ($typeIds) {
            $query->whereIn('products.type_id', $typeIds);
        }

        if ($collectionIds) {
            $query->whereExists(fn ($q) => $q->select(DB::raw(1))
                ->from('product_variants as v')
                ->join('collection_color_sets as ccs', 'ccs.color_set_id', '=', 'v.color_set_id')
                ->whereColumn('v.product_id', 'products.id')
                ->whereIn('ccs.collection_id', $collectionIds));
        }

        if ($materialIds) {
            $query->whereExists(fn ($q) => $q->select(DB::raw(1))
                ->from('product_materials as pm')
                ->whereColumn('pm.product_id', 'products.id')
                ->whereIn('pm.material_id', $materialIds));
        }
    }

    /** Only pieces with a live photograph, or with none ($has = false). */
    public function scopePhotographed(Builder $query, bool $has = true): void
    {
        $exists = fn ($q) => $q->select(DB::raw(1))->from('product_images as i')
            ->whereColumn('i.product_id', 'products.id')->whereNull('i.deleted_at');

        $has ? $query->whereExists($exists) : $query->whereNotExists($exists);
    }

    /**
     * The storefront's order: a shopper scanning a grid should not page past
     * pieces with nothing to look at. The dashboard keeps insertion order,
     * where an unphotographed piece is the one the owners are looking for.
     */
    public function scopePhotographedFirst(Builder $query): void
    {
        $query->orderByRaw('EXISTS (SELECT 1 FROM product_images i WHERE i.product_id = products.id AND i.deleted_at IS NULL) DESC');
    }

    /**
     * Sets `collectionRefs` on each product: the collections that gather the
     * colour sets it is offered in, by name, each once.
     */
    public static function attachCollections(EloquentCollection $products): EloquentCollection
    {
        $byProduct = DB::table('product_variants as v')
            ->join('collection_color_sets as ccs', 'ccs.color_set_id', '=', 'v.color_set_id')
            ->join('collections as col', 'col.id', '=', 'ccs.collection_id')
            ->whereIn('v.product_id', $products->modelKeys())
            ->distinct()
            ->orderBy('v.product_id')->orderBy('col.name')
            ->get(['v.product_id', 'col.id', 'col.name'])
            ->groupBy('product_id');

        foreach ($products as $product) {
            $product->setRelation('collectionRefs', ($byProduct[$product->id] ?? collect())
                ->map(fn ($row) => ['id' => $row->id, 'name' => $row->name])->values()->all());
        }

        return $products;
    }

    public function loadDetail(): static
    {
        $this->load(self::DETAIL);
        self::attachCollections(new EloquentCollection([$this]));

        return $this;
    }

    /**
     * How many pieces sit behind each filter option, unfiltered: a count that
     * moved whenever another filter changed would be a different question. A
     * piece made of two materials counts under both.
     */
    public static function facets(?string $search = null, array $typeIds = [], array $collectionIds = [], array $materialIds = []): array
    {
        // The same filters as the list, so the counts answer for what is on screen.
        $matching = self::query()->filtered($search, $typeIds, $collectionIds, $materialIds)->select('products.id')->toBase();
        $rows = fn ($query) => $query->get()->map(fn ($row) => ['id' => $row->id, 'count' => (int) $row->count])->all();

        return [
            'total' => (clone $matching)->count(),
            'types' => $rows(DB::table('products')->whereIn('id', clone $matching)
                ->groupBy('type_id')->select('type_id as id', DB::raw('COUNT(*) AS count'))),
            'collections' => $rows(DB::table('collection_color_sets as ccs')
                ->join('product_variants as v', 'v.color_set_id', '=', 'ccs.color_set_id')
                ->whereIn('v.product_id', clone $matching)
                ->groupBy('ccs.collection_id')
                ->select('ccs.collection_id as id', DB::raw('COUNT(DISTINCT v.product_id) AS count'))),
            'materials' => $rows(DB::table('product_materials')->whereIn('product_id', clone $matching)
                ->groupBy('material_id')->select('material_id as id', DB::raw('COUNT(*) AS count'))),
        ];
    }

    /** The rows go; the photographs' files stay on disk until the sweep. */
    public function remove(): void
    {
        DB::transaction(function () {
            ProductImage::withTrashed()->where('product_id', $this->id)->forceDelete();
            $this->materials()->detach();
            $this->sizes()->detach();
            $this->variants()->delete();
            $this->delete();
        });
    }
}
