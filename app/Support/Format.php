<?php

namespace App\Support;

use Illuminate\Support\Carbon;
use Illuminate\Support\Str;
use Throwable;

/** How the rendered pages spell dates and social links. */
class Format
{
    private const MONTHS = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
    ];

    /**
     * "12 - 20 de Agosto de 2025", collapsing whatever the two ends share. An
     * unparseable value comes back as it was rather than breaking the page.
     */
    public static function eventDates(mixed $startsOn, mixed $endsOn = null): string
    {
        $start = self::date($startsOn);
        if ($start === null) {
            return (string) ($startsOn ?? '');
        }

        $full = fn (Carbon $d) => "{$d->day} de ".self::MONTHS[$d->month - 1]." de {$d->year}";

        $end = self::date($endsOn);
        if ($end === null || $end->equalTo($start)) {
            return $full($start);
        }
        if ($start->year !== $end->year) {
            return $full($start).' - '.$full($end);
        }
        if ($start->month !== $end->month) {
            return "{$start->day} de ".self::MONTHS[$start->month - 1]." - {$end->day} de ".self::MONTHS[$end->month - 1]." de {$end->year}";
        }

        return "{$start->day} - {$end->day} de ".self::MONTHS[$start->month - 1]." de {$start->year}";
    }

    /**
     * The profile name out of a social URL: "coisascomgosto.vianadocastelo".
     * static/js/dashboard/contacts.js mirrors this so its preview agrees.
     */
    public static function socialHandle(?string $url): ?string
    {
        $handle = Str::afterLast(trim((string) parse_url((string) $url, PHP_URL_PATH), '/'), '/');

        return $handle !== '' ? $handle : $url;
    }

    private static function date(mixed $value): ?Carbon
    {
        if ($value === null || $value === '') {
            return null;
        }
        try {
            return Carbon::createFromFormat('!Y-m-d', substr((string) $value, 0, 10)) ?: null;
        } catch (Throwable) {
            return null;
        }
    }
}
