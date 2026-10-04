<?php

namespace App\Http\Controllers;

use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;

abstract class Controller
{
    public const DEFAULT_LIMIT = 10;

    // public/static/js/core/api.js asks for exactly this many and refuses a list that
    // came back short of its total, so the two have to agree.
    public const MAX_LIMIT = 100;

    /**
     * The JSON body, checked against $rules. A field that is absent is fine
     * unless the rule says `present`; a field that is present must be the right
     * type, null included — the old API's schema refused an explicit null too.
     */
    protected function payload(Request $request, array $rules, array $messages = []): array
    {
        return Validator::make($request->json()->all(), $rules, $messages)->validate();
    }

    /** [page, limit, offset] from the query string, 400 on nonsense. */
    protected function paging(Request $request): array
    {
        $page = $this->positiveInt($request, 'page', 1);
        $limit = min($this->positiveInt($request, 'limit', self::DEFAULT_LIMIT), self::MAX_LIMIT);

        return [$page, $limit, ($page - 1) * $limit];
    }

    protected function envelope(int $total, int $page, int $limit): array
    {
        return ['total' => $total, 'page' => $page, 'pages' => intdiv($total + $limit - 1, $limit), 'limit' => $limit];
    }

    /**
     * A page of $query under $key, searched by name when ?q= is given.
     * $prepare sees the page's models before they are serialised.
     */
    protected function pageOf(Request $request, $query, string $key, string $resource, array $searchColumns = ['name'], ?callable $prepare = null): array
    {
        [$page, $limit, $offset] = $this->paging($request);

        $term = trim((string) $request->query('q'));
        if ($term !== '') {
            $query->where(function ($q) use ($term, $searchColumns) {
                foreach ($searchColumns as $column) {
                    $q->orWhere($column, 'like', "%{$term}%");
                }
            });
        }

        $total = (clone $query)->toBase()->getCountForPagination();
        $rows = $query->offset($offset)->limit($limit)->get();
        if ($prepare) {
            $prepare($rows);
        }

        return [
            $key => $resource::collection($rows)->resolve($request),
            'pagination' => $this->envelope($total, $page, $limit),
        ];
    }

    /**
     * @template T of \Illuminate\Database\Eloquent\Model
     *
     * @param  class-string<T>  $model
     * @return T
     */
    protected function findOr404(string $model, int $id, string $label)
    {
        return $model::find($id) ?? $this->fail(404, "{$label} #{$id} not found");
    }

    /** 409 when the name is taken; $except lets a rename keep its own name. */
    protected function rejectTakenName(string $model, string $label, string $name, ?int $except = null, ?string $message = null): void
    {
        $taken = $model::where('name', $name)->when($except, fn ($q) => $q->where('id', '<>', $except))->exists();

        if ($taken) {
            $lower = strtolower($label);
            $this->fail(409, $message ?? ($except
                ? "{$label} name '{$name}' is already used by another {$lower}."
                : "The {$lower} '{$name}' already exists."));
        }
    }

    /** 404 naming every id in $ids that $model has no row for, in one message. */
    protected function rejectUnknownIds(string $model, array $ids, string $label): void
    {
        $missing = array_values(array_diff($ids, $model::whereIn('id', $ids)->pluck('id')->all()));
        if ($missing) {
            sort($missing);
            $this->fail(404, "Unknown {$label} IDs: [".implode(', ', $missing).']');
        }
    }

    protected function fail(int $status, string $message): never
    {
        throw new HttpResponseException(response()->json(['message' => $message], $status));
    }

    /** Ids from a query parameter that may repeat: ?type_id=1&type_id=5. */
    protected function idList(Request $request, string $key): array
    {
        preg_match_all('/(?:^|&)'.preg_quote($key, '/').'(?:%5B%5D|\[\])?=([^&]*)/', (string) $request->server('QUERY_STRING'), $m);

        return array_values(array_filter(array_map(
            fn ($v) => filter_var(urldecode($v), FILTER_VALIDATE_INT, ['flags' => FILTER_NULL_ON_FAILURE]),
            $m[1],
        ), fn ($v) => $v !== null));
    }

    private function positiveInt(Request $request, string $key, int $default): int
    {
        $raw = $request->query($key, $default);
        $value = filter_var($raw, FILTER_VALIDATE_INT, ['flags' => FILTER_NULL_ON_FAILURE]);

        if ($value === null) {
            $this->fail(400, "'{$key}' must be an integer, got '{$raw}'");
        }
        if ($value < 1) {
            $this->fail(400, "'{$key}' must be 1 or greater, got {$value}");
        }

        return $value;
    }
}
