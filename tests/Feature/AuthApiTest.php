<?php

use App\Http\Controllers\Api\AuthController;
use App\Models\User;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\RateLimiter;

/** werkzeug.security.generate_password_hash('Passw0rd!') */
const AUTH_WERKZEUG_HASH = 'scrypt:32768:8:1$v4sxhndOBsLgppOy$af13201efdbad484d43ce0518a0239858fa68bc209dc6237c939ec3c0cc9805328e48f899b26632e6c37610e1b21c993ab21e3a0ff76a16c4ce74b1fa0df686f';

function authLogin(string $username = 'alice', ?string $password = 'Passw0rd!')
{
    return test()->postJson('/api/auth/login', array_filter(['username' => $username, 'password' => $password], fn ($v) => $v !== null));
}

// Every account can rewrite the whole catalogue, so none is made from the open
// web: the API used to register anyone who asked.
describe('making an account', function () {
    it('is not something the API offers', function () {
        $this->postJson('/api/auth/register', ['username' => 'eve', 'email' => 'eve@example.com', 'password' => 'pw'])
            ->assertClientError();

        expect(User::where('username', 'eve')->exists())->toBeFalse();
    });

    it('is done from the console, with a hashed password', function () {
        $this->artisan('app:create-user', ['username' => 'alice'])
            ->expectsQuestion('E-mail (used for the account only; nothing is sent)', 'alice@example.com')
            ->expectsQuestion('Password', 'Passw0rd!')
            ->expectsQuestion('Repeat the password', 'Passw0rd!')
            ->expectsOutput('Account created: alice')
            ->assertSuccessful();

        $user = User::firstWhere('username', 'alice');
        expect($user->email)->toBe('alice@example.com')
            ->and(Hash::check('Passw0rd!', $user->password))->toBeTrue();
        authLogin()->assertOk();
    });

    it('refuses what the console is given wrong', function (string $username, string $email, string $password, string $repeat) {
        makeUser('taken', email: 'taken@example.com');

        $this->artisan('app:create-user', ['username' => $username])
            ->expectsQuestion('E-mail (used for the account only; nothing is sent)', $email)
            ->expectsQuestion('Password', $password)
            ->expectsQuestion('Repeat the password', $repeat)
            ->assertFailed();

        expect(User::count())->toBe(1);
    })->with([
        'passwords that differ' => ['bea', 'bea@example.com', 'Passw0rd!', 'outra'],
        'an empty password' => ['bea', 'bea@example.com', '', ''],
        'an invalid e-mail' => ['bea', 'no@tld', 'Passw0rd!', 'Passw0rd!'],
        'a taken username' => ['taken', 'bea@example.com', 'Passw0rd!', 'Passw0rd!'],
        'a taken e-mail' => ['bea', 'taken@example.com', 'Passw0rd!', 'Passw0rd!'],
        'a username too long' => [str_repeat('b', 81), 'bea@example.com', 'Passw0rd!', 'Passw0rd!'],
    ]);
});

describe('signing in', function () {
    it('returns the user for valid credentials', function () {
        makeUser('alice');

        authLogin()->assertOk()->assertJsonPath('user.username', 'alice');
    });

    it('never returns the password', function () {
        makeUser('alice');

        $body = authLogin()->json();
        expect($body)->not->toHaveKey('password')
            ->and($body['user'])->not->toHaveKey('password');
    });

    it('answers 401 for a wrong password', function () {
        makeUser('alice');

        authLogin(password: 'wrong')->assertUnauthorized();
    });

    it('answers 404 for an unknown username', function () {
        authLogin('nobody', 'pw')->assertNotFound();
    });

    it('still answers 400 for a missing username', function () {
        $this->postJson('/api/auth/login', ['password' => 'pw'])->assertStatus(400);
    });

    it('signs the browser in', function () {
        $alice = makeUser('alice');

        authLogin();

        expect(Auth::id())->toBe($alice->id);
    });
});

// The login page asks for the username first and the password on a second
// screen, and picks which screen from the status code.
describe('asking whether an account exists', function () {
    it('answers 401 for a known username', function () {
        makeUser('alice');

        authLogin(password: null)->assertUnauthorized();
    });

    it('answers 404 for an unknown username', function () {
        authLogin('nobody', null)->assertNotFound();
    });

    // Hashing on every visit to the login page is a way to make the server do
    // something expensive for free.
    it('never reaches the stored hash', function () {
        makeUser('alice');
        Hash::shouldReceive('check')->never();

        authLogin(password: null)->assertUnauthorized();
    });

    // Otherwise opening the login page six times would lock the owners out.
    it('is not counted as a failed attempt', function () {
        makeUser('alice');
        foreach (range(1, AuthController::FAILURES_ALLOWED + 2) as $_) {
            authLogin(password: null);
        }

        authLogin()->assertOk();
    });
});

describe('guessing is counted', function () {
    beforeEach(fn () => makeUser('alice'));

    it('refuses the attempt after the allowance', function () {
        foreach (range(1, AuthController::FAILURES_ALLOWED) as $_) {
            authLogin(password: 'wrong')->assertUnauthorized();
        }

        expect(authLogin(password: 'wrong')->assertStatus(429)->json('message'))->toContain('failed attempts');
    });

    it('still lets the right password in before the limit', function () {
        foreach (range(1, AuthController::FAILURES_ALLOWED - 1) as $_) {
            authLogin(password: 'wrong');
        }

        authLogin()->assertOk();
    });

    // The attacker's next guess could be the right one.
    it('holds the lockout even against the right password', function () {
        foreach (range(1, AuthController::FAILURES_ALLOWED) as $_) {
            authLogin(password: 'wrong');
        }

        authLogin()->assertStatus(429);
    });

    it('clears the record on signing in', function () {
        foreach (range(1, AuthController::FAILURES_ALLOWED - 1) as $_) {
            authLogin(password: 'wrong');
        }
        authLogin();

        foreach (range(1, AuthController::FAILURES_ALLOWED) as $_) {
            authLogin(password: 'wrong')->assertUnauthorized();
        }
    });

    it('counts per username', function () {
        makeUser('bob');
        foreach (range(1, AuthController::FAILURES_ALLOWED + 1) as $_) {
            authLogin(password: 'wrong');
        }

        authLogin('bob')->assertOk();
    });

    it('lets failures age out of the window', function () {
        foreach (range(1, AuthController::FAILURES_ALLOWED) as $_) {
            authLogin(password: 'wrong');
        }
        authLogin(password: 'wrong')->assertStatus(429);

        $this->travel(AuthController::WINDOW_SECONDS + 1)->seconds();

        authLogin()->assertOk();
    });

    // Counting refusals would let someone who keeps knocking keep the owners
    // locked out for as long as they care to.
    it('does not extend the lockout on a refusal', function () {
        foreach (range(1, AuthController::FAILURES_ALLOWED + 5) as $_) {
            authLogin(password: 'wrong');
        }

        expect(RateLimiter::attempts('login:alice'))->toBe(AuthController::FAILURES_ALLOWED);
    });

    it('counts an unknown username too', function () {
        foreach (range(1, AuthController::FAILURES_ALLOWED) as $_) {
            authLogin('ghost', 'x')->assertNotFound();
        }

        authLogin('ghost', 'x')->assertStatus(429);
    });
});

describe('signing out', function () {
    it('clears the session', function () {
        makeUser('alice');
        authLogin();

        $this->postJson('/api/auth/logout')->assertOk();

        $this->assertGuest();
    });

    it('is not an error without a session', function () {
        $this->postJson('/api/auth/logout')->assertOk()->assertJsonPath('message', 'No user logged in');
    });
});

// Accounts made by the Flask app carry a Werkzeug scrypt hash. Each check takes
// about three seconds, so this is the only test that pays for one.
describe('a password hash from the Flask app', function () {
    it('signs in once by scrypt, then by bcrypt', function () {
        $alice = makeUser('alice');
        $alice->forceFill(['password' => AUTH_WERKZEUG_HASH])->save();

        authLogin()->assertOk();
        $rehashed = $alice->refresh()->password;
        Auth::logout();

        expect($rehashed)->toStartWith('$2y$')
            ->and(Hash::check('Passw0rd!', $rehashed))->toBeTrue();
        authLogin()->assertOk();
        authLogin(password: 'wrong')->assertUnauthorized();
    });
});
