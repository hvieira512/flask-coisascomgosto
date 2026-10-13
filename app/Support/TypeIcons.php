<?php

namespace App\Support;

/**
 * The icon drawn on a piece that has no photograph yet. A type may carry its own
 * Font Awesome class, chosen on the Tipos page; otherwise one is guessed from its
 * name. Product responses carry the resolved icon, so the browser keeps no copy
 * of this table. /product-types deliberately does not resolve it: the dashboard
 * offers "Adivinhar pelo nome" only while it can tell a guess from a choice.
 */
class TypeIcons
{
    public const DEFAULT = 'fa-gift';

    // First match wins, so specific shapes precede generic containers.
    private const ICONS = [
        '/cora[çc][ãa]o|heart/iu' => 'fa-heart',
        '/moldura|quadro|frame|foto/iu' => 'fa-image',
        '/bastidor|hoop/iu' => 'fa-circle-notch',
        '/escova|brush|cabelo/iu' => 'fa-brush',
        '/redond|circul|round/iu' => 'fa-circle-dot',
        '/caixa|box|estojo/iu' => 'fa-box',
        '/len[çc]o|pano|tecido|cloth/iu' => 'fa-scroll',
        '/[íi]man|magnet/iu' => 'fa-magnet',
        '/chave|key/iu' => 'fa-key',
    ];

    public static function for(?string $icon, ?string $name): string
    {
        if ($icon) {
            return $icon;
        }

        foreach (self::ICONS as $pattern => $guess) {
            if (preg_match($pattern, (string) $name)) {
                return $guess;
            }
        }

        return self::DEFAULT;
    }
}
