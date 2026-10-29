<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/**
 * The shop's own details: one row, always id 1, edited in place. The WhatsApp
 * number is the phone number.
 */
class Contact extends Model
{
    public $timestamps = false;

    public $incrementing = false;

    protected $fillable = ['address', 'email', 'whatsapp', 'maps_url', 'facebook_url', 'instagram_url'];

    public static function shop(): ?self
    {
        return static::find(1);
    }

    /** wa.me takes digits only, so spaces, dashes and the leading + go. */
    public function whatsappUrl(): ?string
    {
        $digits = preg_replace('/\D/', '', (string) $this->whatsapp);

        return $digits === '' ? null : "https://wa.me/{$digits}";
    }
}
