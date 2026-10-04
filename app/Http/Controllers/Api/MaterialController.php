<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\MaterialResource;
use App\Models\Material;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

/** What a piece is made of. A lookup the owners maintain themselves. */
class MaterialController extends Controller
{
    private const RULES = ['name' => ['present', 'string']];

    /** List materials, searched by name with ?q=. */
    public function index(Request $request): array
    {
        return $this->pageOf($request, Material::query()->orderBy('id'), 'materials', MaterialResource::class);
    }

    public function store(Request $request): JsonResponse
    {
        $data = $this->payload($request, self::RULES);
        $this->rejectTakenName(Material::class, 'Material', $data['name']);

        return (new MaterialResource(Material::create($data)))->response()->setStatusCode(201);
    }

    public function show(int $material): MaterialResource
    {
        return new MaterialResource($this->findOr404(Material::class, $material, 'Material'));
    }

    public function update(Request $request, int $material): MaterialResource
    {
        $data = $this->payload($request, self::RULES);
        $row = $this->findOr404(Material::class, $material, 'Material');
        $this->rejectTakenName(Material::class, 'Material', $data['name'], $row->id);

        $row->update($data);

        return new MaterialResource($row);
    }

    /** The pieces made of it keep existing, and keep any other materials. */
    public function destroy(int $material): MaterialResource
    {
        $row = $this->findOr404(Material::class, $material, 'Material');

        DB::transaction(function () use ($row) {
            DB::table('product_materials')->where('material_id', $row->id)->delete();
            $row->delete();
        });

        return new MaterialResource($row);
    }
}
