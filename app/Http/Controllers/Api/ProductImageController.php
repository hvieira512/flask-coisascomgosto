<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\ImageResource;
use App\Models\Product;
use App\Models\ProductImage;
use App\Models\ProductVariant;
use App\Support\UploadError;
use App\Support\Uploads;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * Photographs of a piece, uploaded or referenced by path. Every one belongs to
 * a colour: a piece looks different in each colourway.
 */
class ProductImageController extends Controller
{
    private const RULES = [
        'url' => ['present', 'string'],
        'alt' => ['sometimes', 'string'],
        'position' => ['sometimes', 'integer:strict'],
        'variant_id' => ['present', 'integer:strict'],
    ];

    /** A piece's photographs in display order, or one colour's with ?variant_id=. */
    public function index(Request $request, int $product): array
    {
        $this->product($product);

        $variantId = filter_var($request->query('variant_id'), FILTER_VALIDATE_INT, ['flags' => FILTER_NULL_ON_FAILURE]);
        $images = ProductImage::where('product_id', $product)
            ->when($variantId !== null, fn ($q) => $q->where('variant_id', $variantId))
            ->orderBy('position')->orderBy('id')->get();

        return ImageResource::collection($images)->resolve();
    }

    /** Attach a photograph already served from somewhere, by its URL. */
    public function store(Request $request, int $product): JsonResponse
    {
        $data = $this->payload($request, self::RULES);
        $this->product($product);
        $this->variantOf($data['variant_id'], $product);

        $image = ProductImage::create([
            'product_id' => $product,
            'variant_id' => $data['variant_id'],
            'url' => $data['url'],
            'alt' => $data['alt'] ?? null,
            'position' => $data['position'] ?? 0,
        ]);

        return (new ImageResource($image->refresh()))->response()->setStatusCode(201);
    }

    /** Upload a photograph and attach it to one of the piece's colours. */
    public function upload(Request $request, int $product): JsonResponse
    {
        $variantId = filter_var($request->input('variant_id'), FILTER_VALIDATE_INT, ['flags' => FILTER_NULL_ON_FAILURE]);
        if ($variantId === null) {
            $this->fail(400, 'variant_id: The colour set this photograph shows. Required: a piece looks different in each colour, so every photograph belongs to one.');
        }
        if (! $request->hasFile('file')) {
            $this->fail(400, 'file: Photograph: jpg, png or webp, up to 5 MB');
        }

        $this->product($product);
        $this->variantOf($variantId, $product);

        try {
            $url = Uploads::save($request->file('file'));
        } catch (UploadError $error) {
            $this->fail(400, $error->getMessage());
        }

        $image = ProductImage::create([
            'product_id' => $product,
            'variant_id' => $variantId,
            'url' => $url,
            'alt' => $request->input('alt'),
        ]);

        return (new ImageResource($image->refresh()))->response()->setStatusCode(201);
    }

    /** Change a photograph's URL, alt text, position or colour. */
    public function update(Request $request, int $product, int $image): ImageResource
    {
        $data = $this->payload($request, self::RULES);
        $row = $this->imageOf($image, $product);
        $this->variantOf($data['variant_id'], $product);

        $row->update([
            'url' => $data['url'],
            'alt' => $data['alt'] ?? null,
            'variant_id' => $data['variant_id'],
            'position' => $data['position'] ?? 0,
        ]);

        return new ImageResource($row);
    }

    /** Marks it removed. The row and the file both stay until the sweep. */
    public function destroy(int $product, int $image): ImageResource
    {
        $row = $this->imageOf($image, $product);
        $row->delete();

        return new ImageResource($row);
    }

    private function product(int $id): void
    {
        if (! Product::whereKey($id)->exists()) {
            $this->fail(404, "Product #{$id} not found");
        }
    }

    private function variantOf(int $variantId, int $productId): void
    {
        if (! ProductVariant::where(['id' => $variantId, 'product_id' => $productId])->exists()) {
            $this->fail(404, "Variant #{$variantId} does not belong to product #{$productId}");
        }
    }

    private function imageOf(int $imageId, int $productId): ProductImage
    {
        return ProductImage::where(['id' => $imageId, 'product_id' => $productId])->first()
            ?? $this->fail(404, "Image #{$imageId} does not belong to product #{$productId}");
    }
}
