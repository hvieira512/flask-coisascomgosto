<?php

namespace App\Providers;

use App\Models\Contact;
use Dedoc\Scramble\Scramble;
use Dedoc\Scramble\Support\Generator\OpenApi;
use Dedoc\Scramble\Support\Generator\Operation;
use Dedoc\Scramble\Support\Generator\Response as ApiResponse;
use Dedoc\Scramble\Support\Generator\SecurityScheme;
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
    private const PLACEHOLDER_SECRETS = ['dev-jwt-secret-change-me-it-is-in-the-repository'];

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

        // A padlock on every operation behind AuthenticateApi, and on
        // /auth/refresh, which takes the refresh token in the same header.
        Scramble::configure()
            ->withDocumentTransformers(fn (OpenApi $openApi) => $openApi->secure(SecurityScheme::http('bearer', 'JWT')->as('Bearer')))
            ->withOperationTransformers(function (Operation $operation, RouteInfo $route) {
                if (in_array('auth.api', $route->route->gatherMiddleware(), true)) {
                    $operation->addResponse(ApiResponse::make(401)->setDescription('Missing, malformed or expired access token, and no session'));
                    if (! in_array('GET', $route->route->methods(), true)) {
                        $operation->addResponse(ApiResponse::make(403)->setDescription('Session-authenticated write without the X-Requested-With header'));
                    }
                } elseif ($route->route->uri() !== 'api/auth/refresh') {
                    $operation->security = [];
                }
            });

        JsonResource::withoutWrapping();

        // What the dashboard's rail says beside each section: four numbers on the
        // chrome of every page, so one query for all of them.
        View::composer('dashboard.components.sidebar', fn ($view) => $view->with('counts', DB::selectOne(
            'SELECT (SELECT COUNT(*) FROM products) AS pieces, (SELECT COUNT(*) FROM color_sets) AS color_sets, '
            .'(SELECT COUNT(*) FROM collections) AS collections, (SELECT COUNT(*) FROM events) AS events'
        )));

        // The shop's own details, for the footer and the enquiry button.
        // The one failure swallowed is the table not existing yet, between a clone
        // and the first migration: the person setting the project up should see a
        // shop, not a stack trace. Anything else propagates — a shop quietly
        // serving no contact details is worse than an error that says so.
        View::composer(['store.components.footer', 'store.product'], function ($view) {
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
        if (! $this->app->runningInConsole()) {
            $secret = (string) config('jwt.secret');

            if (! config('app.debug') && in_array($secret, self::PLACEHOLDER_SECRETS, true)) {
                throw new RuntimeException('JWT_SECRET_KEY is still the development value from .env.example, so tokens would be signed with a public key. Set a real secret before serving with APP_DEBUG off.');
            }

            // HS256 wants a key at least as long as its hash; php-jwt refuses a
            // shorter one at the first sign-in, which would surface as a 500 there.
            if (strlen($secret) < 32) {
                throw new RuntimeException('JWT_SECRET_KEY must be at least 32 bytes. Generate one with: php -r "echo bin2hex(random_bytes(32));"');
            }
        }
    }
}
