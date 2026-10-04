<?php

namespace App\Providers;

use App\Models\Contact;
use Dedoc\Scramble\Scramble;
use Dedoc\Scramble\Support\Generator\Operation;
use Dedoc\Scramble\Support\Generator\SecurityRequirement;
use Dedoc\Scramble\Support\RouteInfo;
use Illuminate\Database\QueryException;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\View;
use Illuminate\Support\ServiceProvider;
use RuntimeException;

class AppServiceProvider extends ServiceProvider
{
    // The values .env.example ships. They are public, so a deployment signing
    // with one could have its sessions and tokens forged.
    private const PLACEHOLDER_SECRETS = ['dev-jwt-secret-change-me'];

    // MySQL's ER_NO_SUCH_TABLE.
    private const NO_SUCH_TABLE = 1146;

    public function register(): void
    {
        // The docs keep the addresses they had: /api/docs and /api/swagger.json.
        Scramble::ignoreDefaultRoutes();
    }

    public function boot(): void
    {
        Scramble::registerUiRoute('api/docs');
        Scramble::registerJsonSpecificationRoute('api/swagger.json');

        // /auth/refresh takes the refresh token in the Authorization header, so
        // it wears the padlock although no session can stand in for it.
        Scramble::configure()->withOperationTransformers(function (Operation $operation, RouteInfo $route) {
            if ($route->route->uri() === 'api/auth/refresh') {
                $operation->addSecurity(new SecurityRequirement('Bearer'));
            }
        });

        JsonResource::withoutWrapping();

        // What the dashboard's rail says beside each section: four numbers on the
        // chrome of every page, so one query for all of them.
        View::composer('dashboard.components.sidebar', fn ($view) => $view->with('counts', DB::selectOne(
            'SELECT (SELECT COUNT(*) FROM products) AS pieces, (SELECT COUNT(*) FROM color_sets) AS color_sets, '
            .'(SELECT COUNT(*) FROM collections) AS collections, (SELECT COUNT(*) FROM events) AS events'
        )));

        // The shop's own details, for the contact cards and the enquiry button.
        // The one failure swallowed is the table not existing yet, between a clone
        // and the first migration: the person setting the project up should see a
        // shop, not a stack trace. Anything else propagates — a shop quietly
        // serving no contact details is worse than an error that says so.
        View::composer(['store.components.contacts', 'store.product'], function ($view) {
            try {
                $contact = Contact::shop();
            } catch (QueryException $error) {
                if (($error->errorInfo[1] ?? null) !== self::NO_SUCH_TABLE) {
                    throw $error;
                }
                $contact = null;
            }
            $view->with('contact', $contact ?? new Contact);
        });

        // migrate:fresh, migrate:reset, migrate:refresh and db:wipe drop the
        // accounts with everything else, and once that logged the owners out of
        // their own dashboard. The test suite rebuilds its own schema.
        DB::prohibitDestructiveCommands(! $this->app->runningUnitTests());

        // Loud rather than convenient: a deployment that serves normally with a
        // known key looks exactly like one that is safe. Not in the console, so
        // the image can be built and migrations run without the secret.
        if (! $this->app->runningInConsole() && ! config('app.debug')
            && in_array(config('jwt.secret'), [...self::PLACEHOLDER_SECRETS, null, ''], true)) {
            throw new RuntimeException('JWT_SECRET_KEY is unset or still the development value from .env.example, so tokens would be signed with a public key. Set a real secret before serving with APP_DEBUG off.');
        }
    }
}
