<?php

namespace App\Http\Middleware;

use App\Support\Jwt;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Symfony\Component\HttpFoundation\Response;

/**
 * The guard on every write, and on the few reads that are not public.
 *
 * Two credentials reach these endpoints: a bearer token from an API client, and
 * the session cookie the dashboard's own fetch() calls carry. Either way the
 * answer on failure is JSON, never a redirect — the callers would parse a login
 * page as a payload.
 *
 * Accepting the cookie is what makes CSRF possible, so a session write must also
 * carry X-Requested-With. A cross-site form cannot set a header at all, and a
 * cross-site fetch() that sets one turns into a preflight this API does not
 * answer, so only our own code can produce it.
 */
class AuthenticateApi
{
    public const REQUIRED_HEADER = 'X-Requested-With';

    public function handle(Request $request, Closure $next): Response
    {
        $signedIn = Auth::check();

        // A cross-site GET cannot be read back, so a read needs only the cookie.
        if ($signedIn && ($request->isMethodSafe() || $request->hasHeader(self::REQUIRED_HEADER))) {
            $request->attributes->set('user_id', Auth::id());

            return $next($request);
        }

        // A session write with no header still falls through to a token, so the
        // docs' Authorize button works from a browser that also holds a session.
        if ($signedIn && ! $request->hasHeader('Authorization')) {
            return response()->json(['message' => self::REQUIRED_HEADER.' header required for session-authenticated writes'], 403);
        }

        $token = Jwt::fromHeader($request->header('Authorization'));
        if ($token === null) {
            return response()->json(['message' => 'Missing Authorization Header'], 401);
        }

        $claims = Jwt::decode($token, 'access');
        if ($claims === null) {
            return response()->json(['message' => 'Invalid or expired access token'], 401);
        }

        $request->attributes->set('user_id', (int) $claims->sub);

        return $next($request);
    }
}
