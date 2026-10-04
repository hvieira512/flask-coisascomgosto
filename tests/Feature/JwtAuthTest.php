<?php

use App\Support\Jwt;
use Firebase\JWT\JWT as FirebaseJwt;
use Firebase\JWT\Key;

/*
 * The bearer-token half of authentication. Login also signs the test client in
 * by session, which would pass every guard below on its own, so the session is
 * dropped after the token pair is issued.
 */

const JWT_GUARDED = ['/api/users/', '/api/users/1', '/api/contacts/', '/api/auth/me'];

function jwtTokens(string $username = 'apiclient'): array
{
    $pair = tokens($username);
    auth()->logout();
    test()->getJson('/api/auth/me')->assertUnauthorized();

    return $pair;
}

function jwtBearer(string $token): array
{
    return ['Authorization' => "Bearer {$token}"];
}

/** The swagger.json the docs page renders. */
function jwtSpec(): array
{
    return test()->getJson('/api/swagger.json')->assertOk()->json();
}

/** An operation inherits the document's security unless it states its own. */
function jwtIsGuarded(array $spec, array $operation): bool
{
    return ! empty($operation['security'] ?? $spec['security'] ?? []);
}

describe('issuing tokens', function () {
    it('returns an access and a refresh token on login', function () {
        $body = jwtTokens();

        expect($body['access_token'])->not->toBeEmpty()
            ->and($body['refresh_token'])->not->toBeEmpty()
            ->and($body['access_token'])->not->toBe($body['refresh_token']);
    });

    it('also returns the user', function () {
        $body = jwtTokens();

        expect($body['user']['username'])->toBe('apiclient')
            ->and($body['user'])->not->toHaveKey('password');
    });

    it('issues no token for a bad password', function () {
        makeUser('alice');

        $response = $this->postJson('/api/auth/login', ['username' => 'alice', 'password' => 'wrong'])->assertUnauthorized();

        expect($response->json())->not->toHaveKey('access_token');
    });

    // So saying who acted needs no database round trip.
    it('carries the username claim and no is_admin', function () {
        $claims = (array) FirebaseJwt::decode(jwtTokens()['access_token'], new Key(config('jwt.secret'), 'HS256'));

        expect($claims['username'])->toBe('apiclient')
            ->and($claims)->not->toHaveKey('is_admin')
            ->and($claims['type'])->toBe('access')
            ->and($claims['sub'])->toBeString();
    });
});

describe('guards', function () {
    it('answers 401 with no credential', function (string $path) {
        $this->getJson($path)->assertUnauthorized();
    })->with(JWT_GUARDED);

    it('accepts a bearer token', function (string $path) {
        $access = jwtTokens()['access_token'];

        expect($this->getJson($path, jwtBearer($access))->status())->not->toBe(401);
    })->with(JWT_GUARDED);

    it('lets a bearer token authorise a write', function () {
        $access = jwtTokens()['access_token'];

        $this->postJson('/api/materials/', ['name' => 'Cortiça'], jwtBearer($access))->assertCreated();
    });

    it('rejects a garbage token', function () {
        $this->getJson('/api/users/', jwtBearer('not-a-jwt'))->assertUnauthorized()->assertJsonStructure(['message']);
    });

    it('rejects a token without the Bearer prefix', function () {
        $access = jwtTokens()['access_token'];

        $this->getJson('/api/users/', ['Authorization' => $access])->assertUnauthorized();
    });

    it('keeps the catalogue reads public', function (string $path) {
        $this->getJson($path)->assertOk();
    })->with(['/api/products/', '/api/materials/', '/api/collections/']);
});

describe('refreshing', function () {
    it('mints a new access token from a refresh token', function () {
        $refresh = jwtTokens()['refresh_token'];

        expect($this->postJson('/api/auth/refresh', [], jwtBearer($refresh))->assertOk()->json('access_token'))->not->toBeEmpty();
    });

    it('mints an access token that works', function () {
        $refresh = jwtTokens()['refresh_token'];
        $fresh = $this->postJson('/api/auth/refresh', [], jwtBearer($refresh))->json('access_token');

        $this->getJson('/api/users/', jwtBearer($fresh))->assertOk();
    });

    it('refuses an access token', function () {
        $access = jwtTokens()['access_token'];

        $this->postJson('/api/auth/refresh', [], jwtBearer($access))->assertUnauthorized();
    });

    it('answers 401 without a token', function () {
        $this->postJson('/api/auth/refresh')->assertUnauthorized();
    });

    it('rejects an expired access token, then refreshes it', function () {
        $pair = jwtTokens();
        $claims = (array) Jwt::decode($pair['access_token'], 'access');
        $expired = FirebaseJwt::encode([...$claims, 'exp' => time() - 60], config('jwt.secret'), 'HS256');

        $this->getJson('/api/users/', jwtBearer($expired))->assertUnauthorized();

        $fresh = $this->postJson('/api/auth/refresh', [], jwtBearer($pair['refresh_token']))->json('access_token');
        $this->getJson('/api/users/', jwtBearer($fresh))->assertOk();
    });
});

describe('me', function () {
    it('returns the token owner', function () {
        $access = jwtTokens()['access_token'];

        $this->getJson('/api/auth/me', jwtBearer($access))->assertJsonPath('username', 'apiclient');
    });

    it('never returns the password', function () {
        $access = jwtTokens()['access_token'];

        expect($this->getJson('/api/auth/me', jwtBearer($access))->json())->not->toHaveKey('password');
    });
});

describe('the swagger document', function () {
    // This is what renders the Authorize button in /api/docs.
    it('publishes the bearer security scheme', function () {
        $spec = jwtSpec();

        expect($spec['components']['securitySchemes']['Bearer'])->toMatchArray(['type' => 'http', 'scheme' => 'bearer'])
            ->and($spec['security'])->toBe([['Bearer' => []]]);
    });

    it('puts the padlock on a guarded endpoint', function () {
        $spec = jwtSpec();

        expect(jwtIsGuarded($spec, $spec['paths']['/users']['get']))->toBeTrue();
    });

    it('leaves the padlock off a public endpoint', function () {
        $spec = jwtSpec();

        expect(jwtIsGuarded($spec, $spec['paths']['/products']['get']))->toBeFalse();
    });

    // Every write anyone may reach without an account: registering, signing in
    // and out, and a shopper recording that they opened a piece. /auth/refresh is
    // absent on purpose: it takes the refresh token and wears the padlock. A new
    // public write has to be added here deliberately, which is the point.
    it('guards every write except the ones meant to be public', function () {
        $spec = jwtSpec();

        $public = [];
        foreach ($spec['paths'] as $path => $operations) {
            foreach (array_intersect_key($operations, array_flip(['post', 'put', 'patch', 'delete'])) as $verb => $operation) {
                if (! jwtIsGuarded($spec, $operation)) {
                    $public[] = strtoupper($verb)." {$path}";
                }
            }
        }

        expect($public)->toEqualCanonicalizing([
            'POST /auth/register', 'POST /auth/login', 'POST /auth/logout', 'POST /storefront-events',
        ]);
    });
});
