<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\ColorSetResource;
use App\Models\Collection;
use App\Models\Color;
use App\Models\ColorSet;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

/**
 * Named colour combinations pieces are offered in. Named once and shared, so the
 * name is unique across the catalogue and `collection_ids` is a list.
 */
class ColorSetController extends Controller
{
    private const RULES = [
        'name' => ['present', 'string', 'max:120'],
        'collection_ids' => ['sometimes', 'list'],
        'collection_ids.*' => ['integer:strict'],
        'color_ids' => ['present', 'list'],
        'color_ids.*' => ['integer:strict'],
    ];

    /** List colour sets, searched by name with ?q=, or only one collection's with ?collection_id=. */
    public function index(Request $request): array
    {
        $query = ColorSet::withDetail()->orderBy('color_sets.id');

        $collectionId = filter_var($request->query('collection_id'), FILTER_VALIDATE_INT, ['flags' => FILTER_NULL_ON_FAILURE]);
        if ($collectionId !== null) {
            $query->whereHas('collections', fn ($q) => $q->where('collections.id', $collectionId));
        }

        return $this->pageOf($request, $query, 'color_sets', ColorSetResource::class, ['color_sets.name']);
    }

    public function store(Request $request): JsonResponse
    {
        $data = $this->payload($request, self::RULES);
        $this->checkReferences($data);
        $this->rejectTaken($data['name']);

        $set = DB::transaction(function () use ($data) {
            $set = ColorSet::create(['name' => $data['name']]);
            $set->setColors($data['color_ids']);
            $set->collections()->sync(array_unique($data['collection_ids'] ?? []));

            return $set;
        });

        return (new ColorSetResource($this->find($set->id)))->response()->setStatusCode(201);
    }

    public function show(int $colorSet): ColorSetResource
    {
        return new ColorSetResource($this->find($colorSet));
    }

    /** Replaces its name, colours and collections wholesale. */
    public function update(Request $request, int $colorSet): ColorSetResource
    {
        $data = $this->payload($request, self::RULES);
        $set = $this->find($colorSet);
        $this->checkReferences($data);
        $this->rejectTaken($data['name'], $set->id);

        DB::transaction(function () use ($set, $data) {
            $set->update(['name' => $data['name']]);
            $set->setColors($data['color_ids']);
            $set->collections()->sync(array_unique($data['collection_ids'] ?? []));
        });

        return new ColorSetResource($this->find($set->id));
    }

    /** Every variant offered in it goes with it, and their photographs' rows. */
    public function destroy(int $colorSet): ColorSetResource
    {
        $set = $this->find($colorSet);
        $set->remove();

        return new ColorSetResource($set);
    }

    private function checkReferences(array $data): void
    {
        foreach ($data['collection_ids'] ?? [] as $id) {
            if (! Collection::whereKey($id)->exists()) {
                $this->fail(404, "The collection #{$id} does not exist.");
            }
        }

        $this->rejectUnknownIds(Color::class, $data['color_ids'], 'colour');
    }

    private function rejectTaken(string $name, ?int $except = null): void
    {
        $this->rejectTakenName(ColorSet::class, 'Colour set', $name, $except, "The colour set '{$name}' already exists.");
    }

    private function find(int $id): ColorSet
    {
        return ColorSet::withDetail()->find($id) ?? $this->fail(404, "Colour set #{$id} not found");
    }
}
