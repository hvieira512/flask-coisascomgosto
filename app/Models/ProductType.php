<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Facades\DB;

/**
 * The family a piece belongs to: "Caixa", "Coração", "Moldura". Flat — the
 * shape lives in the product's own name.
 */
class ProductType extends Model
{
    public $timestamps = false;

    protected $fillable = ['name', 'description', 'icon'];

    public function products(): HasMany
    {
        return $this->hasMany(Product::class, 'type_id');
    }

    /** How many pieces it holds, as `pieces`. */
    public function scopeWithPieces(Builder $query): void
    {
        $query->withCount(['products as pieces']);
    }

    /** Sets the `cover` of each type, from one query. */
    public static function attachCovers(iterable $types): void
    {
        $types = collect($types);
        $covers = self::covers($types->map(fn (self $type) => $type->id)->all());

        foreach ($types as $type) {
            $type->setRelation('cover', $covers[$type->id] ?? null);
        }
    }

    /**
     * One photograph per type to stand for the family: the first photograph of
     * the earliest piece, so the choice is stable across requests.
     *
     * @return array<int, array{url: string, alt: string}>
     */
    public static function covers(array $typeIds): array
    {
        if ($typeIds === []) {
            return [];
        }

        $ranked = DB::table('product_images as i')
            ->join('products as p', 'p.id', '=', 'i.product_id')
            ->whereIn('p.type_id', $typeIds)
            ->whereNull('i.deleted_at')
            ->select('p.type_id', 'i.url', DB::raw('IFNULL(i.alt, p.name) AS alt'))
            ->selectRaw('ROW_NUMBER() OVER (PARTITION BY p.type_id ORDER BY i.product_id, i.position, i.id) AS rank_in_type');

        return DB::query()->fromSub($ranked, 'ranked')->where('rank_in_type', 1)->get()
            ->mapWithKeys(fn ($row) => [$row->type_id => ['url' => $row->url, 'alt' => $row->alt]])
            ->all();
    }
}
