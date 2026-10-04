<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\ProductTypeResource;
use App\Models\ProductType;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * The family a piece belongs to. Each one reads with how many pieces it holds
 * and a photograph of one of them, so the dashboard need not fetch every product
 * to count.
 */
class ProductTypeController extends Controller
{
    private const RULES = [
        'name' => ['present', 'string'],
        'description' => ['sometimes', 'string'],
        'icon' => ['sometimes', 'string'],
    ];

    /** List product types, searched by name with ?q=. */
    public function index(Request $request): array
    {
        return $this->pageOf($request, ProductType::withPieces()->orderBy('id'), 'product_types', ProductTypeResource::class,
            prepare: ProductType::attachCovers(...));
    }

    public function store(Request $request): JsonResponse
    {
        $data = $this->payload($request, self::RULES);
        $this->rejectTaken($data['name']);

        $type = ProductType::create($data);

        return (new ProductTypeResource($this->find($type->id)))->response()->setStatusCode(201);
    }

    public function show(int $productType): ProductTypeResource
    {
        return new ProductTypeResource($this->find($productType));
    }

    public function update(Request $request, int $productType): ProductTypeResource
    {
        $data = $this->payload($request, self::RULES);
        $type = $this->find($productType);
        $this->rejectTaken($data['name'], $type->id);

        $type->update([
            'name' => $data['name'],
            'description' => $data['description'] ?? null,
            'icon' => $data['icon'] ?? null,
        ]);

        return new ProductTypeResource($this->find($type->id));
    }

    /**
     * Every piece must have a type, so one still in use has nowhere for its
     * pieces to land: move them first.
     */
    public function destroy(int $productType): ProductTypeResource
    {
        $type = $this->find($productType);

        if ($type->pieces) {
            $this->fail(409, $type->pieces.($type->pieces === 1 ? ' product still uses' : ' products still use').' this type. Move them to another type first.');
        }

        $type->delete();

        return new ProductTypeResource($type);
    }

    private function find(int $id): ProductType
    {
        $type = ProductType::withPieces()->find($id) ?? $this->fail(404, "Product type #{$id} not found");
        ProductType::attachCovers([$type]);

        return $type;
    }

    private function rejectTaken(string $name, ?int $except = null): void
    {
        if (ProductType::where('name', $name)->when($except, fn ($q) => $q->where('id', '<>', $except))->exists()) {
            $this->fail(409, "The product type '{$name}' already exists.");
        }
    }
}
