<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\SizeResource;
use App\Models\Size;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

/**
 * The sizes pieces come in. A piece may name one as its default and list the
 * ones it is available in; with none listed it is sold only in its default.
 */
class SizeController extends Controller
{
    private const RULES = ['name' => ['present', 'string'], 'position' => ['sometimes', 'integer:strict']];

    /** List sizes in display order, searched by name with ?q=. */
    public function index(Request $request): array
    {
        return $this->pageOf($request, Size::query()->orderBy('position')->orderBy('id'), 'sizes', SizeResource::class);
    }

    public function store(Request $request): JsonResponse
    {
        $data = $this->payload($request, self::RULES);
        $this->rejectTakenName(Size::class, 'Size', $data['name']);

        $size = Size::create(['name' => $data['name'], 'position' => $data['position'] ?? 0]);

        return (new SizeResource($size->refresh()))->response()->setStatusCode(201);
    }

    public function show(int $size): SizeResource
    {
        return new SizeResource($this->findOr404(Size::class, $size, 'Size'));
    }

    public function update(Request $request, int $size): SizeResource
    {
        $data = $this->payload($request, self::RULES);
        $row = $this->findOr404(Size::class, $size, 'Size');
        $this->rejectTakenName(Size::class, 'Size', $data['name'], $row->id);

        $row->update(['name' => $data['name'], 'position' => $data['position'] ?? 0]);

        return new SizeResource($row);
    }

    /** Pieces listing it lose it, and a piece using it as its default has none. */
    public function destroy(int $size): SizeResource
    {
        $row = $this->findOr404(Size::class, $size, 'Size');

        DB::transaction(function () use ($row) {
            DB::table('product_sizes')->where('size_id', $row->id)->delete();
            DB::table('products')->where('default_size_id', $row->id)->update(['default_size_id' => null]);
            $row->delete();
        });

        return new SizeResource($row);
    }
}
