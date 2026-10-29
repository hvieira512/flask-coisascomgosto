<?php

namespace App\Support;

use App\Models\User;
use Firebase\JWT\JWT as FirebaseJwt;
use Firebase\JWT\Key;
use Illuminate\Support\Str;
use Throwable;

/**
 * The API's bearer tokens: a short-lived access token and a long-lived refresh
 * token, HS256 over JWT_SECRET_KEY. The claims are the ones flask-jwt-extended
 * wrote — `sub` as a string id, `type` access or refresh, `username` — so a
 * token issued before the move to Laravel is still accepted after it.
 */
class Jwt
{
    public static function issue(User $user, string $type): string
    {
        $now = time();
        $lifetime = $type === 'refresh'
            ? config('jwt.refresh_days') * 86400
            : config('jwt.access_minutes') * 60;

        return FirebaseJwt::encode([
            'fresh' => false,
            'iat' => $now,
            'jti' => (string) Str::uuid(),
            'type' => $type,
            'sub' => (string) $user->id,
            'nbf' => $now,
            'exp' => $now + $lifetime,
            'username' => $user->username,
        ], self::key(), 'HS256');
    }

    /** The claims of a valid, unexpired token of this type, or null. */
    public static function decode(string $token, string $type): ?object
    {
        try {
            $claims = FirebaseJwt::decode($token, new Key(self::key(), 'HS256'));
        } catch (Throwable) {
            return null;
        }

        return ($claims->type ?? null) === $type ? $claims : null;
    }

    private static function key(): string
    {
        return (string) config('jwt.secret');
    }
}
