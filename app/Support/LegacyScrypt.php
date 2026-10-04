<?php

namespace App\Support;

/**
 * Verifies the Werkzeug hashes the Flask app wrote: "scrypt:N:r:p$salt$hex".
 *
 * PHP has no scrypt of its own, so this is the algorithm (RFC 7914) by hand.
 * It takes about three seconds per check, which is paid once per account:
 * User::checkPassword rehashes with bcrypt on the first right answer.
 *
 * ponytail: dead code once no users.password starts with "scrypt:". Delete it
 * then, with the branch in User::checkPassword.
 */
class LegacyScrypt
{
    public static function owns(string $hash): bool
    {
        return str_starts_with($hash, 'scrypt:');
    }

    public static function check(string $password, string $hash): bool
    {
        if (! preg_match('/^scrypt:(\d+):(\d+):(\d+)\$([^$]+)\$([0-9a-f]+)$/', $hash, $m)) {
            return false;
        }
        [, $n, $r, $p, $salt, $expected] = $m;

        $derived = self::derive($password, $salt, (int) $n, (int) $r, (int) $p, intdiv(strlen($expected), 2));

        return hash_equals($expected, bin2hex($derived));
    }

    private static function derive(string $password, string $salt, int $n, int $r, int $p, int $length): string
    {
        $blocks = hash_pbkdf2('sha256', $password, $salt, 1, $p * 128 * $r, true);
        $mixed = '';

        for ($k = 0; $k < $p; $k++) {
            $x = array_values(unpack('V*', substr($blocks, $k * 128 * $r, 128 * $r)));
            $words = 32 * $r;
            // Packed strings rather than arrays: N arrays of 32r ints would need
            // several hundred MB at N=32768.
            $v = [];
            for ($i = 0; $i < $n; $i++) {
                $v[$i] = pack('V*', ...$x);
                $x = self::blockMix($x, $r);
            }
            for ($i = 0; $i < $n; $i++) {
                $vj = unpack('V*', $v[$x[$words - 16] & ($n - 1)]);
                for ($w = 0; $w < $words; $w++) {
                    $x[$w] ^= $vj[$w + 1];
                }
                $x = self::blockMix($x, $r);
            }
            $mixed .= pack('V*', ...$x);
        }

        return hash_pbkdf2('sha256', $password, $mixed, 1, $length, true);
    }

    private static function blockMix(array $b, int $r): array
    {
        $x = array_slice($b, (2 * $r - 1) * 16, 16);
        $even = [];
        $odd = [];

        for ($i = 0; $i < 2 * $r; $i++) {
            for ($w = 0; $w < 16; $w++) {
                $x[$w] ^= $b[$i * 16 + $w];
            }
            $x = self::salsa($x);
            if ($i % 2 === 0) {
                array_push($even, ...$x);
            } else {
                array_push($odd, ...$x);
            }
        }

        return array_merge($even, $odd);
    }

    /** Salsa20/8 core over sixteen 32-bit words. */
    private static function salsa(array $b): array
    {
        $x = $b;
        // Unrolled: a closure per quarter-round makes each check take twice as long.
        $quarters = [[0, 4, 8, 12], [5, 9, 13, 1], [10, 14, 2, 6], [15, 3, 7, 11],
            [0, 1, 2, 3], [5, 6, 7, 4], [10, 11, 8, 9], [15, 12, 13, 14]];

        for ($round = 0; $round < 4; $round++) {
            foreach ($quarters as [$a, $bb, $c, $d]) {
                $t = ($x[$a] + $x[$d]) & 0xFFFFFFFF;
                $x[$bb] ^= (($t << 7) | ($t >> 25)) & 0xFFFFFFFF;
                $t = ($x[$bb] + $x[$a]) & 0xFFFFFFFF;
                $x[$c] ^= (($t << 9) | ($t >> 23)) & 0xFFFFFFFF;
                $t = ($x[$c] + $x[$bb]) & 0xFFFFFFFF;
                $x[$d] ^= (($t << 13) | ($t >> 19)) & 0xFFFFFFFF;
                $t = ($x[$d] + $x[$c]) & 0xFFFFFFFF;
                $x[$a] ^= (($t << 18) | ($t >> 14)) & 0xFFFFFFFF;
            }
        }

        for ($i = 0; $i < 16; $i++) {
            $x[$i] = ($x[$i] + $b[$i]) & 0xFFFFFFFF;
        }

        return $x;
    }
}
