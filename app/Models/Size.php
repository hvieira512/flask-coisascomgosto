<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/** Pequeno, Médio, Grande: the owners' words, ordered by position. */
class Size extends Model
{
    public $timestamps = false;

    protected $fillable = ['name', 'position'];
}
