<?php

namespace App\Http\Resources;

use App\Support\TypeIcons;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\Product */
class ProductResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $variants = VariantResource::collection($this->variants)->resolve($request);

        // The tile a listing shows: the first photograph of the first colour that
        // has one.
        $primary = collect($variants)->first(fn ($variant) => $variant['images'] !== [])['images'][0] ?? null;

        return [
            'id' => $this->id,
            'name' => $this->name,
            'description' => $this->description,
            'type' => [
                'id' => $this->type->id,
                'name' => $this->type->name,
                'icon' => TypeIcons::for($this->type->icon, $this->type->name),
            ],
            'materials' => MaterialResource::collection($this->materials),
            'collections' => $this->resource->getRelation('collectionRefs'),
            'default_size' => $this->defaultSize ? new SizeResource($this->defaultSize) : null,
            'sizes' => SizeResource::collection($this->sizes),
            'variants' => $variants,
            'primary_image' => $primary,
        ];
    }
}
