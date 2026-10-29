<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Query\Builder;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

/**
 * One thing a visitor did. Counters only: the table has no column that could
 * hold anything about the person.
 */
class StorefrontEvent extends Model
{
    public $timestamps = false;

    public const KINDS = ['visit', 'view', 'enquiry', 'search', 'filter'];

    public const TERM_MAX = 120;

    protected $fillable = ['kind', 'product_id', 'variant_id', 'size_id', 'facet', 'facet_label', 'term', 'results'];

    // The figures the dashboard shows, in its order. Shared by the totals and the
    // daily series behind each, so a new figure is added once.
    public const TOTALS = ['visits', 'views', 'pieces', 'enquiries', 'searches'];

    private const FIGURES = "SUM(kind = 'visit') AS visits, SUM(kind = 'view') AS views, "
        ."SUM(kind = 'enquiry') AS enquiries, SUM(kind = 'search') AS searches, "
        ."COUNT(DISTINCT CASE WHEN kind = 'view' THEN product_id END) AS pieces";

    public static function tidy(string $text): string
    {
        return mb_substr(implode(' ', preg_split('/\s+/u', trim($text))), 0, self::TERM_MAX);
    }

    /**
     * Everything the dashboard's home page shows for the last $days days, with
     * the window before it so each figure can say which way it is going.
     * Aggregated in SQL: a GROUP BY has no hundred-row ceiling.
     */
    public static function overview(int $days, int $top = 8): array
    {
        $started = DB::table('storefront_events')->min('created_at');

        return [
            'window' => [
                'days' => $days,
                // Before the first event there is no history, which is a
                // different thing from a quiet week.
                'counting_since' => $started ? str_replace(' ', 'T', $started) : null,
            ],
            'totals' => self::totals($days, 0),
            'daily' => self::daily($days),
            'previous' => self::totals($days, $days),
            'top_products' => self::window($days)
                ->join('products as p', 'p.id', '=', 'e.product_id')
                ->whereIn('e.kind', ['view', 'enquiry'])
                ->groupBy('p.id', 'p.name')
                ->selectRaw("p.id, p.name, SUM(e.kind = 'view') AS views, SUM(e.kind = 'enquiry') AS enquiries")
                ->orderByDesc('views')->orderByDesc('enquiries')->orderBy('p.name')
                ->limit($top)->get()
                ->map(fn ($r) => ['id' => $r->id, 'name' => $r->name, 'views' => (int) $r->views, 'enquiries' => (int) $r->enquiries])
                ->all(),
            // Which colourways get asked about: the answer to "what next".
            'top_color_sets' => self::window($days)
                ->join('product_variants as v', 'v.id', '=', 'e.variant_id')
                ->join('color_sets as cs', 'cs.id', '=', 'v.color_set_id')
                ->where('e.kind', 'enquiry')
                ->groupBy('cs.id', 'cs.name')
                ->selectRaw('cs.id, cs.name, COUNT(*) AS enquiries')
                ->orderByDesc('enquiries')->orderBy('cs.name')
                ->limit($top)->get()
                ->map(fn ($r) => ['id' => $r->id, 'name' => $r->name, 'enquiries' => (int) $r->enquiries])
                ->all(),
            'top_filters' => self::window($days)
                ->where('kind', 'filter')->whereNotNull('facet_label')
                ->groupBy('facet', 'facet_label')
                ->selectRaw('facet, facet_label AS label, COUNT(*) AS count')
                ->orderByDesc('count')->orderBy('facet')->orderBy('facet_label')
                ->limit($top)->get()
                ->map(fn ($r) => ['facet' => $r->facet, 'label' => $r->label, 'count' => (int) $r->count])
                ->all(),
        ];
    }

    /**
     * How many pieces were added in the window, or null when the window reaches
     * back past the earliest dated piece: every piece that predates dating
     * carries the date the column arrived, and counting those would report the
     * whole back catalogue as new.
     */
    public static function piecesAdded(int $days): ?int
    {
        $earliest = DB::table('products')->min('created_at');
        $honest = $earliest === null
            || DB::selectOne('SELECT NOW() - INTERVAL ? DAY > ? AS honest', [$days, $earliest])->honest;

        return $honest
            ? DB::table('products')->whereRaw('created_at >= NOW() - INTERVAL ? DAY', [$days])->count()
            : null;
    }

    /**
     * The events of one window, as `e`. $offsetDays shifts it back a whole
     * window. The current one has no upper bound on purpose: DATETIME keeps
     * whole seconds, and `< NOW()` would miss an event from this very second.
     */
    private static function window(int $days, int $offsetDays = 0): Builder
    {
        $query = DB::table('storefront_events as e');

        return $offsetDays === 0
            ? $query->whereRaw('e.created_at >= NOW() - INTERVAL ? DAY', [$days])
            : $query->whereRaw('e.created_at >= NOW() - INTERVAL ? DAY AND e.created_at < NOW() - INTERVAL ? DAY', [$days + $offsetDays, $offsetDays]);
    }

    private static function totals(int $days, int $offsetDays): array
    {
        $row = self::window($days, $offsetDays)->selectRaw(self::FIGURES)->first();

        return array_combine(self::TOTALS, array_map(fn ($key) => (int) $row->{$key}, self::TOTALS));
    }

    /**
     * Each figure's shape over the window, one value per day, silent days as
     * zeros: a line drawn straight from Monday to Friday over a quiet week
     * claims the week was busy. The days are MySQL's, so the series lines up
     * with the totals rather than with the web server's idea of today.
     */
    private static function daily(int $days): array
    {
        $byDay = self::window($days)
            ->selectRaw('DATE(e.created_at) AS day, '.self::FIGURES)
            ->groupBy('day')->get()->keyBy('day');

        $span = DB::selectOne('SELECT DATE(NOW() - INTERVAL ? DAY) AS first, DATE(NOW()) AS last', [$days - 1]);

        $series = array_fill_keys(self::TOTALS, []);
        for ($day = Carbon::parse($span->first); $day->lte($span->last); $day->addDay()) {
            $row = $byDay[$day->toDateString()] ?? null;
            foreach (self::TOTALS as $key) {
                $series[$key][] = $row ? (int) $row->{$key} : 0;
            }
        }

        return $series;
    }
}
