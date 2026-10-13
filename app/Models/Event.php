<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/** A fair, market or show the workshop took part in. */
class Event extends Model
{
    public $timestamps = false;

    protected $fillable = ['name', 'location', 'description', 'starts_on', 'ends_on', 'url'];

    protected function casts(): array
    {
        return ['starts_on' => 'date:Y-m-d', 'ends_on' => 'date:Y-m-d'];
    }
}
