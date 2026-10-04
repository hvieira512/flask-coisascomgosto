<?php

use Illuminate\Support\Facades\DB;

/*
 * The one Laravel migration builds the schema on an empty database, or adopts a
 * database the Flask app already built — but only one that reached the Flask
 * migration 0013. The adoption cases need a database of their own, so each runs
 * against a scratch one, created and dropped as root.
 */

const MIGRATIONS_SCRATCH = 'ccg_c_migrations_test';

const MIGRATIONS_FILE = '2026_10_04_000000_create_catalogue_schema';

const MIGRATIONS_TABLES = [
    'collection_color_sets', 'collections', 'color_set_colors', 'color_sets', 'colors', 'contacts', 'events',
    'materials', 'migrations', 'product_images', 'product_materials', 'product_sizes', 'product_types',
    'product_variants', 'products', 'sizes', 'storefront_events', 'users',
];

function migrationsScratch()
{
    return DB::connection('scratch');
}

function migrationsRun(): void
{
    test()->artisan('migrate', ['--database' => 'scratch', '--force' => true])->assertSuccessful();
}

/** A database the Flask app built, as far as the migration can tell, at the given migrations. */
function migrationsFlaskDatabase(array $applied): void
{
    migrationsScratch()->statement('CREATE TABLE products (id INT PRIMARY KEY)');
    migrationsScratch()->statement('CREATE TABLE schema_migrations (filename VARCHAR(255) PRIMARY KEY)');
    foreach ($applied as $filename) {
        migrationsScratch()->table('schema_migrations')->insert(['filename' => $filename]);
    }
}

function migrationsTables(): array
{
    return collect(migrationsScratch()->select('SHOW TABLES'))->map(fn ($row) => array_values((array) $row)[0])->sort()->values()->all();
}

beforeEach(function () {
    $mysql = config('database.connections.mysql');
    $root = ['username' => 'root', 'password' => env('MYSQL_ROOT_PASSWORD', 'root')];
    config([
        'database.connections.scratch_root' => [...$mysql, ...$root, 'database' => ''],
        'database.connections.scratch' => [...$mysql, ...$root, 'database' => MIGRATIONS_SCRATCH],
    ]);
    DB::connection('scratch_root')->statement('DROP DATABASE IF EXISTS '.MIGRATIONS_SCRATCH);
    DB::connection('scratch_root')->statement('CREATE DATABASE '.MIGRATIONS_SCRATCH.' CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci');
});

afterEach(function () {
    DB::purge('scratch');
    DB::connection('scratch_root')->statement('DROP DATABASE IF EXISTS '.MIGRATIONS_SCRATCH);
});

describe('on an empty database', function () {
    it('builds the whole schema and records it', function () {
        migrationsRun();

        expect(migrationsTables())->toBe(MIGRATIONS_TABLES)
            ->and(migrationsScratch()->table('migrations')->pluck('migration')->all())->toBe([MIGRATIONS_FILE]);
    });

    it('seeds the sizes, accents intact', function () {
        migrationsRun();

        expect(migrationsScratch()->table('sizes')->orderBy('position')->pluck('name')->all())->toBe(['Pequeno', 'Médio', 'Grande']);
    });

    it('writes the cascades into the foreign keys', function () {
        migrationsRun();

        $rules = collect(migrationsScratch()->select(
            'SELECT constraint_name AS name, delete_rule AS rule FROM information_schema.referential_constraints WHERE constraint_schema = ?',
            [MIGRATIONS_SCRATCH],
        ))->pluck('rule', 'name');

        expect($rules)->toHaveCount(17)
            ->and($rules['fk_products_type'])->toBe('RESTRICT')
            ->and($rules['fk_products_default_size'])->toBe('SET NULL')
            ->and($rules['fk_product_images_variant'])->toBe('CASCADE')
            ->and($rules['fk_product_variants_color_set'])->toBe('CASCADE');
    });

    it('does not apply twice', function () {
        migrationsRun();

        $this->artisan('migrate', ['--database' => 'scratch', '--force' => true])
            ->expectsOutputToContain('Nothing to migrate')
            ->assertSuccessful();
    });
});

describe('on a database the Flask app built', function () {
    it('adopts one at 0013 without building over it', function () {
        migrationsFlaskDatabase(['0012_earlier.sql', '0013_a_collection_reaches_a_piece_through_its_colours.sql']);

        migrationsRun();

        expect(migrationsTables())->toBe(['migrations', 'products', 'schema_migrations'])
            ->and(migrationsScratch()->table('migrations')->pluck('migration')->all())->toBe([MIGRATIONS_FILE]);
    });

    // Anything older is a schema the models do not match. A failed migration is
    // not recorded, so it runs again once the database is brought up to date.
    it('refuses one older than 0013, and does not record it', function () {
        migrationsFlaskDatabase(['0012_earlier.sql']);

        expect(fn () => $this->artisan('migrate', ['--database' => 'scratch', '--force' => true])->run())
            ->toThrow(RuntimeException::class, '0013');

        expect(migrationsScratch()->table('migrations')->count())->toBe(0)
            ->and(migrationsTables())->toBe(['migrations', 'products', 'schema_migrations']);
    });
});

it('leaves nothing pending on the test database', function () {
    $this->artisan('migrate:status')->doesntExpectOutputToContain('Pending')->assertSuccessful();
});
