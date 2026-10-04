<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\CollectionResource;
use App\Http\Resources\ColorSetResource;
use App\Models\Collection;
use App\Models\ColorSet;
use App\Support\UploadError;
use App\Support\Uploads;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * Themed groupings such as "Barra da Saia". A collection gathers colour sets —
 * a set may be in several, or in none — and deleting one leaves its colour sets
 * and pieces in place.
 */
class CollectionController extends Controller
{
    private const RULES = [
        'name' => ['present', 'string'],
        'description' => ['sometimes', 'string'],
        'image_url' => ['sometimes', 'string'],
    ];

    /** List collections, searched by name with ?q=. */
    public function index(Request $request): array
    {
        return $this->pageOf($request, Collection::withBorrowedImage()->orderBy('id'), 'collections', CollectionResource::class);
    }

    public function store(Request $request): JsonResponse
    {
        $data = $this->payload($request, self::RULES);
        $this->rejectTakenName(Collection::class, 'Collection', $data['name']);

        $collection = Collection::create($data);

        return (new CollectionResource($this->find($collection->id)))->response()->setStatusCode(201);
    }

    public function show(int $collection): CollectionResource
    {
        return new CollectionResource($this->find($collection));
    }

    public function update(Request $request, int $collection): CollectionResource
    {
        $data = $this->payload($request, self::RULES);
        $row = $this->find($collection);
        $this->rejectTakenName(Collection::class, 'Collection', $data['name'], $row->id);

        $row->update([
            'name' => $data['name'],
            'description' => $data['description'] ?? null,
            'image_url' => $data['image_url'] ?? null,
        ]);

        return new CollectionResource($this->find($row->id));
    }

    /** The cover file stays; the sweep collects it once nothing points at it. */
    public function destroy(int $collection): CollectionResource
    {
        $row = $this->find($collection);
        $row->remove();

        return new CollectionResource($row);
    }

    /** The colour sets this collection gathers. */
    public function colorSets(int $collection): array
    {
        $row = $this->find($collection);

        return ColorSetResource::collection($row->colorSets()->with(['colors', 'collections'])->limit(100)->get())->resolve();
    }

    /**
     * Replace which colour sets this collection gathers. Links rather than
     * moves: a set keeps whatever other collections it is in.
     */
    public function replaceColorSets(Request $request, int $collection): array
    {
        $data = $this->payload($request, [
            'color_set_ids' => ['present', 'list'],
            'color_set_ids.*' => ['integer:strict'],
        ]);
        $row = $this->find($collection);

        $missing = array_values(array_diff($data['color_set_ids'], ColorSet::whereIn('id', $data['color_set_ids'])->pluck('id')->all()));
        if ($missing) {
            sort($missing);
            $this->fail(404, 'Unknown colour set IDs: ['.implode(', ', $missing).']');
        }

        $row->colorSets()->sync(array_unique($data['color_set_ids']));

        return $this->colorSets($row->id);
    }

    /** Upload the photograph that stands for this collection. */
    public function storeCover(Request $request, int $collection): JsonResponse
    {
        $row = $this->find($collection);

        try {
            $url = Uploads::save($request->file('file'), Uploads::COLLECTIONS);
        } catch (UploadError $error) {
            $this->fail(400, $error->getMessage());
        }

        // The file it replaces is left for the sweep. A cover pointed at one of
        // the pieces' own photographs cannot take that photograph with it.
        $row->update(['image_url' => $url]);

        return (new CollectionResource($this->find($row->id)))->response()->setStatusCode(201);
    }

    public function destroyCover(int $collection): CollectionResource
    {
        $row = $this->find($collection);
        $row->update(['image_url' => null]);

        return new CollectionResource($this->find($row->id));
    }

    private function find(int $id): Collection
    {
        return Collection::withBorrowedImage()->find($id) ?? $this->fail(404, "Collection #{$id} not found");
    }
}
