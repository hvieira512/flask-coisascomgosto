<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

/**
 * A photograph of one colourway of a piece.
 *
 * Removing one sets deleted_at and leaves the file: the owners' only copy of a
 * photograph may be the one they uploaded from a phone. `app:sweep-uploads` is
 * the only thing that deletes either, after a grace period.
 */
class ProductImage extends Model
{
    use SoftDeletes;

    public $timestamps = false;

    protected $fillable = ['product_id', 'variant_id', 'url', 'alt', 'position'];
}
