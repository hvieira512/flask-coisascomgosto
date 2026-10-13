<?php

namespace App\Http\Resources;

use App\Models\Contact;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Contact */
class ContactResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'address' => $this->address,
            'email' => $this->email,
            'whatsapp' => $this->whatsapp,
            'whatsapp_url' => $this->whatsappUrl(),
            'maps_url' => $this->maps_url,
            'facebook_url' => $this->facebook_url,
            'instagram_url' => $this->instagram_url,
        ];
    }
}
