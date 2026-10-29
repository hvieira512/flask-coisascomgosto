<?php

use App\Models\ProductType;
use App\Models\User;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Process;

/*
 * Rebuilding the Flask schema once emptied the users table on a real database
 * and left the owners locked out of their own dashboard. Here that is two
 * guarantees: the commands that drop every table refuse to run outside the test
 * suite, and reseeding the catalogue leaves the accounts alone.
 */

function initDbSeed(): void
{
    test()->artisan('db:seed', ['--force' => true])->assertSuccessful();
}

describe('the destructive commands', function () {
    it('refuse to run outside the test suite, and the accounts survive', function (string $command) {
        makeUser('hugo');

        $result = Process::path(base_path())
            ->env(['APP_ENV' => 'local', 'MYSQL_DATABASE' => config('database.connections.mysql.database')])
            ->run([PHP_BINARY, 'artisan', $command, '--force', '--no-interaction']);

        expect($result->failed())->toBeTrue($result->output())
            ->and($result->output())->toContain('prohibited')
            ->and(User::pluck('username')->all())->toBe(['hugo']);
    })->with(['migrate:fresh', 'migrate:reset', 'migrate:refresh', 'db:wipe']);
});

describe('reseeding the catalogue', function () {
    it('keeps the accounts', function () {
        makeUser('hugo');

        initDbSeed();

        expect(User::pluck('username')->all())->toBe(['hugo']);
    });

    // A preserved row that cannot be logged into is no better than none.
    it('keeps the password hash and the email', function () {
        $hugo = makeUser('hugo');

        initDbSeed();

        expect(DB::table('users')->where('username', 'hugo')->first())
            ->password->toBe($hugo->password)
            ->email->toBe('hugo@example.com');
    });

    it('keeps the ids, so references still point at the same person', function () {
        $first = makeUser('hugo');
        $second = makeUser('maria');

        initDbSeed();

        expect(User::orderBy('id')->pluck('username', 'id')->all())->toBe([$first->id => 'hugo', $second->id => 'maria']);
    });

    // Preserving accounts must not turn the reseed into a no-op.
    it('still replaces the catalogue', function () {
        ProductType::create(['name' => 'Tipo de teste']);
        makeUser('hugo');

        initDbSeed();

        expect(ProductType::where('name', 'Tipo de teste')->exists())->toBeFalse()
            ->and(ProductType::where('name', 'Caixa')->exists())->toBeTrue();
    });

    it('does not mind an empty users table', function () {
        initDbSeed();

        expect(User::count())->toBe(0);
    });
});
