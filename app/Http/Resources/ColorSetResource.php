<?php

namespace App\Http\Resources;

use App\Models\ColorSet;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin ColorSet */
class ColorSetResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'collections' => $this->collections->map(fn ($c) => ['id' => $c->id, 'name' => $c->name])->all(),
            'colors' => ColorResource::collection($this->colors),
            'pieces' => (int) $this->pieces,
        ];
    }
}
