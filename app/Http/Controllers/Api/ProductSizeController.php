<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\SizeResource;
use App\Models\Product;
use App\Models\Size;
use Illuminate\Http\Request;

/** The sizes a piece is available in. */
class ProductSizeController extends Controller
{
    public function index(int $product): array
    {
        return SizeResource::collection($this->findOr404(Product::class, $product, 'Product')->sizes)->resolve();
    }

    /** Replace them all. An empty list means only the default size. */
    public function update(Request $request, int $product): array
    {
        $data = $this->payload($request, [
            'size_ids' => ['present', 'list'],
            'size_ids.*' => ['integer:strict'],
        ]);
        $row = $this->findOr404(Product::class, $product, 'Product');
        $this->rejectUnknownIds(Size::class, $data['size_ids'], 'size');

        $row->sizes()->sync(array_unique($data['size_ids']));

        return SizeResource::collection($row->sizes()->get())->resolve();
    }
}
