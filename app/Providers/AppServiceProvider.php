<?php

namespace App\Providers;

use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\ServiceProvider;
use RuntimeException;

class AppServiceProvider extends ServiceProvider
{
    // The values .env.example ships. They are public, so a deployment signing
    // with one could have its sessions and tokens forged.
    private const PLACEHOLDER_SECRETS = ['dev-jwt-secret-change-me'];

    public function boot(): void
    {
        JsonResource::withoutWrapping();

        // migrate:fresh, migrate:reset, migrate:refresh and db:wipe drop the
        // accounts with everything else, and once that logged the owners out of
        // their own dashboard. The test suite rebuilds its own schema.
        DB::prohibitDestructiveCommands(! $this->app->runningUnitTests());

        // Loud rather than convenient: a deployment that boots normally with a
        // known key looks exactly like one that is safe.
        if (! config('app.debug') && in_array(config('jwt.secret'), [...self::PLACEHOLDER_SECRETS, null, ''], true)) {
            throw new RuntimeException('JWT_SECRET_KEY still holds the development value from .env.example, so tokens would be signed with a public key. Set a real secret before starting with APP_DEBUG off.');
        }
    }
}
