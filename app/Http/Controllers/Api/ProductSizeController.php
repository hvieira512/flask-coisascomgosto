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
        return SizeResource::collection($this->product($product)->sizes)->resolve();
    }

    /** Replace them all. An empty list means only the default size. */
    public function update(Request $request, int $product): array
    {
        $data = $this->payload($request, [
            'size_ids' => ['present', 'list'],
            'size_ids.*' => ['integer:strict'],
        ]);
        $row = $this->product($product);

        $missing = array_values(array_diff($data['size_ids'], Size::whereIn('id', $data['size_ids'])->pluck('id')->all()));
        if ($missing) {
            sort($missing);
            $this->fail(404, 'Unknown size IDs: ['.implode(', ', $missing).']');
        }

        $row->sizes()->sync(array_unique($data['size_ids']));

        return SizeResource::collection($row->sizes()->get())->resolve();
    }

    private function product(int $id): Product
    {
        return Product::find($id) ?? $this->fail(404, "Product #{$id} not found");
    }
}
