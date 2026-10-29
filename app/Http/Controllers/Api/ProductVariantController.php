<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\VariantResource;
use App\Models\ColorSet;
use App\Models\Product;
use App\Models\ProductVariant;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/** The colour sets a piece is offered in. */
class ProductVariantController extends Controller
{
    public function index(int $product): array
    {
        $this->findOr404(Product::class, $product, 'Product');

        $variants = ProductVariant::where('product_id', $product)->orderBy('id')
            ->with(['colorSet.colors', 'images'])->get();

        return ['variants' => VariantResource::collection($variants)->resolve()];
    }

    /** Offer this piece in another colour set. */
    public function store(Request $request, int $product): JsonResponse
    {
        $data = $this->payload($request, ['color_set_id' => ['present', 'integer:strict']]);
        $this->findOr404(Product::class, $product, 'Product');
        $setId = $data['color_set_id'];

        if (! ColorSet::whereKey($setId)->exists()) {
            $this->fail(404, "The colour set #{$setId} does not exist.");
        }
        if (ProductVariant::where(['product_id' => $product, 'color_set_id' => $setId])->exists()) {
            $this->fail(409, "Product #{$product} already has a variant in colour set #{$setId}.");
        }

        $variant = ProductVariant::create(['product_id' => $product, 'color_set_id' => $setId]);

        return (new VariantResource($variant->load(['colorSet.colors', 'images'])))->response()->setStatusCode(201);
    }

    /**
     * Stop offering this piece in one colour set. The rows of that colour's
     * photographs go with it; the files stay until the sweep.
     */
    public function destroy(int $product, int $variant): VariantResource
    {
        $this->findOr404(Product::class, $product, 'Product');

        $row = ProductVariant::where(['id' => $variant, 'product_id' => $product])->first()
            ?? $this->fail(404, "Variant #{$variant} does not belong to product #{$product}");
        $row->load(['colorSet.colors', 'images']);
        $row->remove();

        return new VariantResource($row);
    }
}
