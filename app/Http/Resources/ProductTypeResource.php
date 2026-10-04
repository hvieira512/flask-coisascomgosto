<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * `icon` is the type's own choice, null when it has none: the dashboard can only
 * offer "Adivinhar pelo nome" while it can tell a guess from a choice. `image`
 * is the cover ProductType::attachCovers set.
 *
 * @mixin \App\Models\ProductType
 */
class ProductTypeResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'description' => $this->description,
            'icon' => $this->icon,
            'pieces' => (int) $this->pieces,
            'image' => $this->resource->getRelation('cover'),
        ];
    }
}
