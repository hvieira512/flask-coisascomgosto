<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Facades\DB;

/**
 * A named combination of colours, named once and shared: it may appear in
 * several collections, or in none.
 */
class ColorSet extends Model
{
    public $timestamps = false;

    protected $fillable = ['name'];

    public function colors(): BelongsToMany
    {
        return $this->belongsToMany(Color::class, 'color_set_colors')
            ->orderBy('color_set_colors.position');
    }

    public function collections(): BelongsToMany
    {
        return $this->belongsToMany(Collection::class, 'collection_color_sets')->orderBy('collections.name');
    }

    public function variants(): HasMany
    {
        return $this->hasMany(ProductVariant::class);
    }

    /** Exactly these colours, in this order. Duplicates keep their first place. */
    public function setColors(array $colorIds): void
    {
        $positions = [];
        foreach (array_values(array_unique($colorIds)) as $position => $id) {
            $positions[$id] = ['position' => $position];
        }
        $this->colors()->sync($positions);
    }

    /**
     * Deleting a set removes every variant offered in it, through
     * ProductVariant::remove so their photographs go the same way as anywhere
     * else.
     */
    public function remove(): void
    {
        DB::transaction(function () {
            $this->variants()->get()->each->remove();
            $this->colors()->detach();
            $this->collections()->detach();
            $this->delete();
        });
    }
}
