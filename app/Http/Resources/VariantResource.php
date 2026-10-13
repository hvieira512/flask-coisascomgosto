<?php

namespace App\Http\Resources;

use App\Models\ProductVariant;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * No collections on the nested colour set: nothing reading a variant uses them,
 * and a field that is always empty would read as "this set is in none".
 *
 * @mixin ProductVariant
 */
class VariantResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'color_set' => [
                'id' => $this->colorSet->id,
                'name' => $this->colorSet->name,
                'colors' => ColorResource::collection($this->colorSet->colors)->resolve($request),
            ],
            'images' => ImageResource::collection($this->images)->resolve($request),
        ];
    }
}
