<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Support\Facades\DB;

/**
 * A themed grouping such as "Barra da Saia". It gathers colour sets rather than
 * owning them, and reaches a piece only through the colour sets that piece is
 * offered in.
 */
class Collection extends Model
{
    public $timestamps = false;

    protected $fillable = ['name', 'description', 'image_url'];

    public function colorSets(): BelongsToMany
    {
        return $this->belongsToMany(ColorSet::class, 'collection_color_sets')->orderBy('color_sets.id');
    }

    /**
     * What a response shows beside the row itself.
     *
     * pieces: how many pieces its colour sets reach, each once.
     *
     * borrowed_image_url: a photograph of a piece in the collection, so one with
     * no cover of its own still shows something. A colour set shared with fewer
     * collections wins first — Filigrana and Bordados both reach Branco e
     * Dourado, and ordering by recency alone gave the two of them the same
     * photograph side by side. Then the most recent piece.
     */
    public function scopeWithDetail(Builder $query): void
    {
        $query->addSelect(['collections.*', 'pieces' => DB::table('collection_color_sets as cs')
            ->join('product_variants as v', 'v.color_set_id', '=', 'cs.color_set_id')
            ->whereColumn('cs.collection_id', 'collections.id')
            ->selectRaw('COUNT(DISTINCT v.product_id)'),
            'borrowed_image_url' => DB::table('collection_color_sets as cs')
                ->join('product_variants as v', 'v.color_set_id', '=', 'cs.color_set_id')
                ->join('products as p', 'p.id', '=', 'v.product_id')
                ->join('product_images as i', 'i.variant_id', '=', 'v.id')
                ->whereColumn('cs.collection_id', 'collections.id')
                ->whereNull('i.deleted_at')
                ->orderByRaw('(SELECT COUNT(*) FROM collection_color_sets shared WHERE shared.color_set_id = cs.color_set_id)')
                ->orderByDesc('p.created_at')
                // Pieces made in the same second (a seed, an import) tie on the
                // timestamp; without this the cover changes from one load to the next.
                ->orderByDesc('p.id')
                ->orderBy('i.position')
                ->orderBy('i.id')
                ->limit(1)
                ->select('i.url'),
        ]);
    }

    /** Its colour sets and pieces survive it; they stop being gathered here. */
    public function remove(): void
    {
        DB::transaction(function () {
            $this->colorSets()->detach();
            $this->delete();
        });
    }
}
