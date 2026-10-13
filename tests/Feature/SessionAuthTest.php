<?php

use App\Models\User;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Route;

/*
 * The session half of authentication. The dashboard's pages are rendered
 * server-side and cannot carry a token, so they and the API's guard accept the
 * session cookie. The token half is in JwtAuthTest.
 */

const SESSION_GUARDED = ['/api/users/', '/api/users/1', '/api/contacts/', '/api/auth/me'];

/** A signed-in client that sends no X-Requested-With: what a forged cross-site request looks like. */
function sessionForged(): User
{
    $user = makeUser('forged');
    test()->actingAs($user);

    return $user;
}

/** A bearer token, with the session login also gave the client dropped again. */
function sessionAccessToken(): string
{
    $access = tokens()['access_token'];
    Auth::logout();

    return $access;
}

function sessionDashboardPaths(): array
{
    return collect(Route::getRoutes()->getRoutes())
        ->filter(fn ($route) => str_starts_with((string) $route->getName(), 'dashboard.') && in_array('GET', $route->methods()))
        ->map(fn ($route) => '/'.$route->uri())
        ->sort()->values()->all();
}

describe('signing in', function () {
    it('populates the session', function () {
        $alice = makeUser('alice');

        $this->postJson('/api/auth/login', ['username' => 'alice', 'password' => 'Passw0rd!']);

        $this->assertAuthenticatedAs($alice);
    });

    it('leaves the caller anonymous on a bad password', function () {
        makeUser('alice');

        $this->postJson('/api/auth/login', ['username' => 'alice', 'password' => 'wrong'])->assertUnauthorized();

        $this->getJson('/api/auth/me')->assertUnauthorized();
    });

    it('carries across requests', function () {
        signIn();

        $this->getJson('/api/auth/me')->assertOk();
        $this->getJson('/api/auth/me')->assertOk();
    });

    it('authorises a write', function () {
        signIn();

        $this->postJson('/api/materials/', ['name' => 'Vidro'])->assertCreated();
    });
});

describe('guards', function () {
    it('answers 401 when signed out', function (string $path) {
        $this->getJson($path)->assertUnauthorized();
    })->with(SESSION_GUARDED);

    it('lets a signed-in caller through', function (string $path) {
        signIn();

        expect($this->getJson($path)->status())->not->toBe(401);
    })->with(SESSION_GUARDED);

    // A client holding both is not locked out by a stale token.
    it('lets a session win over a broken token', function () {
        signIn();

        $this->getJson('/api/auth/me', ['Authorization' => 'Bearer not-a-jwt'])->assertOk();
    });
});

// The cookie is a credential the browser attaches to any request to this
// origin, including one a third-party page made. X-Requested-With is what
// separates our own code from that page: a cross-site form cannot set a header,
// and a cross-site fetch() that sets one asks for a preflight nobody answers.
describe('cross-site writes cannot use the cookie', function () {
    it('refuses a JSON write without the header', function () {
        sessionForged();

        $response = $this->postJson('/api/materials/', ['name' => 'Latão'])->assertForbidden();

        expect($response->json('message'))->toContain('X-Requested-With');
    });

    // multipart/form-data needs no preflight, so a plain <form> on another site
    // could post to it.
    it('refuses the upload endpoint', function () {
        signIn();
        $product = makeProduct('Tigela');
        sessionForged();

        $this->withoutHeader('X-Requested-With')
            ->post("/api/products/{$product['id']}/images/upload", ['file' => photo('x.jpg')], ['Accept' => 'application/json'])
            ->assertForbidden();
    });

    it('refuses the collection cover', function () {
        signIn();
        $collection = makeCollection('Inverno');
        sessionForged();

        $this->withoutHeader('X-Requested-With')
            ->post("/api/collections/{$collection['id']}/cover", ['file' => photo('x.jpg')], ['Accept' => 'application/json'])
            ->assertForbidden();
    });

    // The API routes no PATCH, so these two are the rest of what a forged
    // request could reach.
    it('covers every unsafe method', function (string $method) {
        sessionForged();

        $this->json($method, '/api/materials/1', ['name' => 'x'])->assertForbidden();
    })->with(['PUT', 'DELETE']);

    // A cross-site GET cannot be read back, so refusing it would protect nothing.
    it('still lets reads through', function () {
        sessionForged();

        $this->getJson('/api/auth/me')->assertOk();
    });

    // curl and Swagger must not have to know about the header.
    it('needs no header with a bearer token', function () {
        $access = sessionAccessToken();

        $this->postJson('/api/materials/', ['name' => 'Cortiça'], ['Authorization' => "Bearer {$access}"])->assertCreated();
    });

    // The Authorize button sends a token, the browser sends the cookie too, and
    // Swagger's own fetch() sets no header of ours.
    it('still lets swagger write from a browser holding a session', function () {
        $access = sessionAccessToken();
        sessionForged();

        $this->postJson('/api/materials/', ['name' => 'Bronze'], ['Authorization' => "Bearer {$access}"])->assertCreated();
    });

    it('guards the contacts PUT', function () {
        $this->putJson('/api/contacts/', ['email' => 'x@y.z'])->assertUnauthorized();
    });

    it('keeps the catalogue reads public', function (string $path) {
        $this->getJson($path)->assertOk();
    })->with(['/api/products/', '/api/materials/', '/api/collections/']);
});

describe('signing out', function () {
    it('empties the session', function () {
        signIn();

        $this->postJson('/api/auth/logout')->assertOk();

        $this->assertGuest();
    });

    it('refuses guarded reads afterwards', function () {
        signIn();
        $this->postJson('/api/auth/logout');

        $this->getJson('/api/auth/me')->assertUnauthorized();
    });

    it('is not an error when signed out', function () {
        $this->postJson('/api/auth/logout')->assertOk()->assertJsonPath('message', 'No user logged in');
    });
});

describe('me', function () {
    it('returns the signed-in account', function () {
        signIn();

        $this->getJson('/api/auth/me')->assertJsonPath('username', 'tokenuser');
    });

    it('never returns the password', function () {
        signIn();

        expect($this->getJson('/api/auth/me')->json())->not->toHaveKey('password');
    });

    // A session can outlive the row it points at.
    it('rejects a stale session', function () {
        signIn((new User(['username' => 'ghost']))->forceFill(['id' => 999999]));

        $this->getJson('/api/auth/me')->assertUnauthorized();
    });
});

describe('documented status codes', function () {
    it('documents the 401 of a guarded endpoint', function () {
        $responses = $this->getJson('/api/swagger.json')->json('paths./users.get.responses');

        expect($responses)->toHaveKey('401');
    });

    it('documents no 401 on a public endpoint', function () {
        $responses = $this->getJson('/api/swagger.json')->json('paths./products.get.responses');

        expect($responses)->not->toHaveKey('401');
    });
});

// Walks the routes the app actually has, so a page added without the guard
// fails here instead of shipping public.
describe('the dashboard pages', function () {
    it('exist to be guarded', function () {
        expect(count(sessionDashboardPaths()))->toBeGreaterThanOrEqual(5);
    });

    it('send an anonymous visitor to the login', function () {
        foreach (sessionDashboardPaths() as $path) {
            $response = $this->get($path);
            expect($response->status())->toBe(302, $path)
                ->and($response->headers->get('Location'))->toContain('/auth');
        }
    });

    // /dashboard itself redirects to /dashboard/home, the one legitimate redirect.
    it('are served to a signed-in visitor', function () {
        signIn();

        foreach (sessionDashboardPaths() as $path) {
            $response = $this->get($path);
            expect($response->status())->toBeIn([200, 302], $path);
            if ($response->status() === 302) {
                expect($response->headers->get('Location'))->not->toContain('/auth');
            }
        }
    });
});
