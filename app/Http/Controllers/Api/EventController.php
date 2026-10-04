<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\EventResource;
use App\Models\Event;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/** The fairs, markets and shows the workshop took part in. */
class EventController extends Controller
{
    private const RULES = [
        'name' => ['present', 'string', 'max:180'],
        'location' => ['sometimes', 'string', 'max:180'],
        'description' => ['sometimes', 'string'],
        'starts_on' => ['present', 'string', 'date_format:Y-m-d'],
        'ends_on' => ['sometimes', 'string', 'date_format:Y-m-d'],
        'url' => ['sometimes', 'string', 'max:500'],
    ];

    /** List events, most recent first, searched by name or location with ?q=. */
    public function index(Request $request): array
    {
        return $this->pageOf($request, Event::query()->orderByDesc('starts_on')->orderByDesc('id'),
            'events', EventResource::class, ['name', 'location']);
    }

    public function store(Request $request): JsonResponse
    {
        $event = Event::create($this->fields($request));

        return (new EventResource($event->refresh()))->response()->setStatusCode(201);
    }

    public function show(int $event): EventResource
    {
        return new EventResource($this->findOr404(Event::class, $event, 'Event'));
    }

    public function update(Request $request, int $event): EventResource
    {
        $fields = $this->fields($request);
        $row = $this->findOr404(Event::class, $event, 'Event');
        $row->update($fields);

        return new EventResource($row->refresh());
    }

    public function destroy(int $event): EventResource
    {
        $row = $this->findOr404(Event::class, $event, 'Event');
        $row->delete();

        return new EventResource($row);
    }

    /** Every field, with the ones left out cleared: a PUT replaces the event. */
    private function fields(Request $request): array
    {
        $data = $this->payload($request, self::RULES);

        return [
            'name' => $data['name'],
            'starts_on' => $data['starts_on'],
            'location' => $data['location'] ?? null,
            'description' => $data['description'] ?? null,
            'ends_on' => $data['ends_on'] ?? null,
            'url' => $data['url'] ?? null,
        ];
    }
}
