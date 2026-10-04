<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\ColorResource;
use App\Models\Color;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

/** The single colours colour sets are built from. */
class ColorController extends Controller
{
    private const RULES = ['name' => ['present', 'string'], 'hex' => ['sometimes', 'string']];

    /** List colours, searched by name with ?q=. */
    public function index(Request $request): array
    {
        return $this->pageOf($request, Color::query()->orderBy('id'), 'colors', ColorResource::class);
    }

    public function store(Request $request): JsonResponse
    {
        $data = $this->payload($request, self::RULES);
        $this->rejectTakenName(Color::class, 'Colour', $data['name']);

        return (new ColorResource(Color::create($data)))->response()->setStatusCode(201);
    }

    public function show(int $color): ColorResource
    {
        return new ColorResource($this->findOr404(Color::class, $color, 'Colour'));
    }

    public function update(Request $request, int $color): ColorResource
    {
        $data = $this->payload($request, self::RULES);
        $row = $this->findOr404(Color::class, $color, 'Colour');
        $this->rejectTakenName(Color::class, 'Colour', $data['name'], $row->id);

        $row->update(['name' => $data['name'], 'hex' => $data['hex'] ?? null]);

        return new ColorResource($row);
    }

    /** Any colour set that used it loses it from its swatches. */
    public function destroy(int $color): ColorResource
    {
        $row = $this->findOr404(Color::class, $color, 'Colour');

        DB::transaction(function () use ($row) {
            DB::table('color_set_colors')->where('color_id', $row->id)->delete();
            $row->delete();
        });

        return new ColorResource($row);
    }
}
