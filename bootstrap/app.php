<?php

use Illuminate\Cookie\Middleware\AddQueuedCookiesToResponse;
use Illuminate\Cookie\Middleware\EncryptCookies;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Foundation\Http\Middleware\ConvertEmptyStringsToNull;
use Illuminate\Foundation\Http\Middleware\TrimStrings;
use Illuminate\Http\Request;
use Illuminate\Routing\Middleware\SubstituteBindings;
use Illuminate\Session\Middleware\StartSession;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        // Stored as sent: an empty description stays "", and a password with a
        // space at either end keeps it.
        $middleware->remove([ConvertEmptyStringsToNull::class, TrimStrings::class]);

        // The API reads the session, because the dashboard's own fetch() calls
        // authenticate with its cookie. No CSRF token: AuthenticateApi demands
        // X-Requested-With on a session write instead, which a cross-site form
        // cannot send.
        $middleware->group('api', [
            EncryptCookies::class,
            AddQueuedCookiesToResponse::class,
            StartSession::class,
            SubstituteBindings::class,
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->shouldRenderJsonWhen(fn (Request $request) => $request->is('api', 'api/*'));

        // A malformed body is the caller's mistake: 400, as the API has always
        // answered, rather than Laravel's 422.
        $exceptions->render(fn (ValidationException $e, Request $request) => $request->is('api/*')
            ? response()->json(['message' => 'Input payload validation failed', 'errors' => $e->errors()], 400)
            : null);

        $exceptions->render(function (HttpExceptionInterface $e, Request $request) {
            if (! $request->is('api', 'api/*')) {
                return null;
            }
            $message = match ($e->getStatusCode()) {
                404 => 'Resource not found',
                405 => 'The method is not allowed for the requested URL.',
                default => $e->getMessage() ?: 'Error',
            };

            return response()->json(['message' => $message], $e->getStatusCode(), $e->getHeaders());
        });
    })->create();
