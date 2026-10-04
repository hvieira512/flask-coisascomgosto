<?php

use Illuminate\Support\Facades\Process;

/*
 * The signing key and the cookie flags. Booted in a subprocess on purpose: the
 * only honest test of "it refuses to start" is starting it, and the test's own
 * application has already booted with the test environment.
 */

/**
 * Boot the app in a fresh PHP with $env over a real secret and print config($key).
 * .env holds APP_DEBUG=true and the placeholder, so each case states its own.
 */
function configBoot(array $env, string $key = 'jwt.secret')
{
    $script = 'require "vendor/autoload.php"; $app = require "bootstrap/app.php";'
        .'$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();'
        .'echo json_encode(config('.var_export($key, true).'));';

    return Process::path(base_path())
        // Booted as the web server is: the console is let through on purpose.
        ->env(['APP_RUNNING_IN_CONSOLE' => 'false', 'JWT_SECRET_KEY' => 'a-real-jwt-secret-of-at-least-32-bytes', ...$env])
        ->run([PHP_BINARY, '-r', $script]);
}

// A deployment signing tokens with a constant from this repository boots and
// serves exactly like a safe one, so this is a refusal to start, not a warning.
describe('the JWT signing key is not optional', function () {
    it('refuses the placeholder outside debug', function () {
        $result = configBoot(['APP_DEBUG' => 'false', 'JWT_SECRET_KEY' => 'dev-jwt-secret-change-me']);

        expect($result->failed())->toBeTrue()
            ->and($result->output().$result->errorOutput())->toContain('JWT_SECRET_KEY')->toContain('.env.example');
    });

    it('refuses an empty key outside debug', function () {
        $result = configBoot(['APP_DEBUG' => 'false', 'JWT_SECRET_KEY' => '']);

        expect($result->failed())->toBeTrue()
            ->and($result->output().$result->errorOutput())->toContain('JWT_SECRET_KEY');
    });

    it('starts with a real key', function () {
        $result = configBoot(['APP_DEBUG' => 'false']);

        expect($result->successful())->toBeTrue($result->errorOutput())
            ->and(json_decode($result->output()))->toBe('a-real-jwt-secret-of-at-least-32-bytes');
    });

    // Otherwise the guard would be something every developer works around.
    it('still runs development on the placeholder', function () {
        $result = configBoot(['APP_DEBUG' => 'true', 'JWT_SECRET_KEY' => 'dev-jwt-secret-change-me']);

        expect($result->successful())->toBeTrue($result->output().$result->errorOutput());
    });

    // So the image can be built and migrations run before the secret exists.
    it('lets the console run on the placeholder', function () {
        $result = configBoot(['APP_RUNNING_IN_CONSOLE' => 'true', 'APP_DEBUG' => 'false', 'JWT_SECRET_KEY' => 'dev-jwt-secret-change-me']);

        expect($result->successful())->toBeTrue($result->output().$result->errorOutput());
    });
});

// AuthenticateApi accepts the session cookie in place of a bearer token, so it
// can write to the whole catalogue.
describe('the session cookie is treated as a credential', function () {
    it('is HttpOnly and SameSite=Lax', function () {
        expect(config('session.http_only'))->toBeTrue()
            ->and(config('session.same_site'))->toBe('lax');
    });

    // No TLS in development, so a Secure cookie there would never be sent;
    // everywhere else it must not travel in clear.
    it('is Secure exactly when debug is off', function () {
        $deployed = configBoot(['APP_DEBUG' => 'false'], 'session.secure');
        $development = configBoot(['APP_DEBUG' => 'true'], 'session.secure');

        expect(json_decode($deployed->output()))->toBeTrue($deployed->errorOutput())
            ->and(json_decode($development->output()))->toBeFalsy();
    });
});
