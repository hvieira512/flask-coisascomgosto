<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Collection;
use App\Models\Color;
use App\Models\ColorSet;
use App\Models\Product;
use App\Models\StorefrontEvent;
use Illuminate\Http\Request;

/** What the dashboard's home page reads, in one request. */
class AnalyticsController extends Controller
{
    public const DEFAULT_DAYS = 7;

    public const MAX_DAYS = 365;

    /**
     * Views, enquiries, searches and filters over the last `days` days. Any
     * window from a day to a year is answerable, so `days` is clamped rather
     * than refused.
     */
    public function overview(Request $request): array
    {
        $days = filter_var($request->query('days'), FILTER_VALIDATE_INT, ['flags' => FILTER_NULL_ON_FAILURE]) ?? self::DEFAULT_DAYS;
        $days = max(1, min($days, self::MAX_DAYS));

        return StorefrontEvent::overview($days) + [
            // Rides along so the page costs one request.
            'catalogue' => [
                'products' => Product::count(),
                'color_sets' => ColorSet::count(),
                'collections' => Collection::count(),
                'colors' => Color::count(),
                // Null when the window starts before pieces were dated at all;
                // the page then leaves the phrase out.
                'added' => StorefrontEvent::piecesAdded($days),
            ],
        ];
    }
}
