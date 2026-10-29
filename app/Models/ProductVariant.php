<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Facades\DB;

/** One piece offered in one colour set. */
class ProductVariant extends Model
{
    public $timestamps = false;

    protected $fillable = ['product_id', 'color_set_id'];

    public function colorSet(): BelongsTo
    {
        return $this->belongsTo(ColorSet::class);
    }

    public function images(): HasMany
    {
        return $this->hasMany(ProductImage::class, 'variant_id')->orderBy('position')->orderBy('id');
    }

    /**
     * Removes the variant and its photographs' rows. The rows go rather than
     * being marked, because a removed photograph of a colour that no longer
     * exists is a state nothing could present. The files stay for the sweep.
     */
    public function remove(): void
    {
        DB::transaction(function () {
            ProductImage::withTrashed()->where('variant_id', $this->id)->forceDelete();
            $this->delete();
        });
    }
}
