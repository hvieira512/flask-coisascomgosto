<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\UserResource;
use App\Models\User;
use App\Support\Jwt;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\RateLimiter;

/**
 * Signing in. Accounts are made with `php artisan app:create-user`, never
 * through the API: every account can rewrite the whole catalogue.
 *
 * Login answers with a token pair for API clients and also signs the browser in,
 * because the rendered dashboard pages cannot carry a token from localStorage.
 */
class AuthController extends Controller
{
    // Five wrong passwords for one username inside fifteen minutes.
    public const FAILURES_ALLOWED = 5;

    public const WINDOW_SECONDS = 15 * 60;

    /**
     * Exchange a username and password for a token pair.
     *
     * 404 and 401 mean different things on purpose: the login page asks for the
     * username first, and draws the password field on 401. That tells whoever
     * asks which names have accounts — two, the owners' own — and it is the
     * price of the two-step page. A username with no password is that first
     * question, and is not counted as a failed attempt.
     */
    public function login(Request $request): JsonResponse
    {
        $data = $this->payload($request, [
            'username' => ['present', 'string'],
            'password' => ['sometimes', 'string'],
        ]);
        $username = $data['username'];
        $password = $data['password'] ?? '';
        $key = "login:{$username}";

        if (RateLimiter::tooManyAttempts($key, self::FAILURES_ALLOWED)) {
            $this->fail(429, 'Too many failed attempts for this username. Wait a few minutes and try again.');
        }

        $user = User::where('username', $username)->first();
        if (! $user) {
            if ($password !== '') {
                RateLimiter::hit($key, self::WINDOW_SECONDS);
            }
            $this->fail(404, 'User invalid.');
        }

        if ($password === '') {
            $this->fail(401, 'This account exists. Send the password.');
        }

        // Refusals are not counted, or the window would never drain while
        // somebody kept knocking.
        if (! $user->checkPassword($password)) {
            RateLimiter::hit($key, self::WINDOW_SECONDS);
            $this->fail(401, 'Invalid login.');
        }

        RateLimiter::clear($key);
        Auth::login($user);
        $request->session()->regenerate();

        return response()->json([
            'access_token' => Jwt::issue($user, 'access'),
            'refresh_token' => Jwt::issue($user, 'refresh'),
            'user' => (new UserResource($user))->resolve(),
        ]);
    }

    /**
     * Send the REFRESH token in the Authorization header for a new access
     * token. The refresh token keeps its original expiry and is not reissued.
     */
    public function refresh(Request $request): JsonResponse
    {
        $token = $request->bearerToken();
        if ($token === null) {
            $this->fail(401, 'Missing Authorization Header');
        }

        $claims = Jwt::decode($token, 'refresh');
        if ($claims === null) {
            $this->fail(401, 'Invalid or expired refresh token');
        }

        $user = User::find((int) $claims->sub) ?? $this->fail(401, 'The account for this token no longer exists.');

        return response()->json([
            'access_token' => Jwt::issue($user, 'access'),
            'refresh_token' => null,
            'user' => (new UserResource($user))->resolve(),
        ]);
    }

    /** The account the caller is signed in as. */
    public function me(Request $request): UserResource
    {
        $user = User::find($request->attributes->get('user_id'));
        if (! $user) {
            Auth::logout();
            $this->fail(401, 'This account no longer exists.');
        }

        return new UserResource($user);
    }

    /**
     * Ends the browser's session. Tokens are stateless and stay valid until
     * they expire; the client discards them.
     */
    public function logout(Request $request): JsonResponse
    {
        $wasSignedIn = Auth::check();
        Auth::logout();
        $request->session()->invalidate();

        return response()->json(['message' => $wasSignedIn ? 'Successfully logged out' : 'No user logged in']);
    }
}
