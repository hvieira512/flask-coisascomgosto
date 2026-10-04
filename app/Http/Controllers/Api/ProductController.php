<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\ProductResource;
use App\Models\Material;
use App\Models\Product;
use App\Models\ProductType;
use App\Models\Size;
use Dedoc\Scramble\Attributes\QueryParameter;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

/**
 * The pieces. Variants, photographs and available sizes are sub-resources;
 * what a piece is made of is here, because it is a fact about the piece and a
 * piece is saved once.
 */
class ProductController extends Controller
{
    private const RULES = [
        'name' => ['present', 'string', 'max:180'],
        'description' => ['present', 'string'],
        'type_id' => ['present', 'integer:strict'],
        'material_ids' => ['sometimes', 'list'],
        'material_ids.*' => ['integer:strict'],
        'default_size_id' => ['sometimes', 'integer:strict'],
    ];

    /**
     * List products. `type_id`, `collection_id` and `material_id` may repeat
     * (several values read as OR); `photographed_first=1` is the storefront's
     * order.
     */
    #[QueryParameter('type_id', 'Only products of this type. Repeatable.', type: 'int')]
    #[QueryParameter('collection_id', 'Only products in this collection, reached through the colour sets it gathers. Repeatable.', type: 'int')]
    #[QueryParameter('material_id', 'Only products made of this material. Repeatable.', type: 'int')]
    #[QueryParameter('page', 'Page number, 1-based (default 1)', type: 'int')]
    #[QueryParameter('limit', 'Items per page, max 100 (default 10)', type: 'int')]
    public function index(Request $request): array
    {
        [$page, $limit, $offset] = $this->paging($request);

        $query = Product::query()->filtered(
            $request->query('q'),
            $this->idList($request, 'type_id'),
            $this->idList($request, 'collection_id'),
            $this->idList($request, 'material_id'),
        );
        $total = (clone $query)->count();

        if (filter_var($request->query('photographed_first'), FILTER_VALIDATE_INT)) {
            $query->photographedFirst();
        }
        $products = $query->orderBy('products.id')->offset($offset)->limit($limit)->with(Product::DETAIL)->get();
        Product::attachCollections($products);

        return [
            'products' => ProductResource::collection($products)->resolve($request),
            'pagination' => $this->envelope($total, $page, $limit),
        ];
    }

    public function store(Request $request): JsonResponse
    {
        $data = $this->payload($request, self::RULES);
        $this->checkReferences($data);

        $this->rejectTakenName(Product::class, 'Product', $data['name'], message: "The product {$data['name']} already exists.");

        $product = DB::transaction(function () use ($data) {
            $product = Product::create($data);
            $product->materials()->sync(array_unique($data['material_ids'] ?? []));

            return $product;
        });

        return (new ProductResource($this->find($product->id)))->response()->setStatusCode(201);
    }

    /** How many products sit behind each filter option, for the catalogue's sidebar. */
    public function facets(): array
    {
        return Product::facets();
    }

    public function show(int $product): ProductResource
    {
        return new ProductResource($this->find($product));
    }

    public function update(Request $request, int $product): ProductResource
    {
        $data = $this->payload($request, self::RULES);
        $row = Product::find($product) ?? $this->fail(404, "Product #{$product} not found");
        $this->checkReferences($data);

        $this->rejectTakenName(Product::class, 'Product', $data['name'], $row->id, "Product name '{$data['name']}' is already used by another product");

        DB::transaction(function () use ($row, $data) {
            $row->update([
                'type_id' => $data['type_id'],
                'name' => $data['name'],
                'description' => $data['description'],
                'default_size_id' => $data['default_size_id'] ?? null,
            ]);
            $row->materials()->sync(array_unique($data['material_ids'] ?? []));
        });

        return new ProductResource($this->find($row->id));
    }

    public function destroy(int $product): ProductResource
    {
        $row = $this->find($product);
        $row->remove();

        return new ProductResource($row);
    }

    private function find(int $id): Product
    {
        return (Product::find($id) ?? $this->fail(404, "Product #{$id} not found"))->loadDetail();
    }

    private function checkReferences(array $data): void
    {
        if (! ProductType::whereKey($data['type_id'])->exists()) {
            $this->fail(404, "The product type #{$data['type_id']} does not exist.");
        }

        $this->rejectUnknownIds(Material::class, $data['material_ids'] ?? [], 'material');

        $sizeId = $data['default_size_id'] ?? null;
        if ($sizeId !== null && ! Size::whereKey($sizeId)->exists()) {
            $this->fail(404, "The size #{$sizeId} does not exist.");
        }
    }
}
