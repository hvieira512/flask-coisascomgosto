<?php

namespace Tests;

use Database\Seeders\LookupSeeder;
use Illuminate\Foundation\Testing\DatabaseTruncation;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\File;
use RuntimeException;

/**
 * Every test starts from the schema's own rows and nothing else. Tables are
 * truncated rather than rolled back, so ids start at 1 each time, and the
 * browser tests — whose server answers outside any transaction — see the same
 * data the test wrote.
 */
abstract class TestCase extends BaseTestCase
{
    use DatabaseTruncation;

    protected function setUp(): void
    {
        parent::setUp();

        // migrate:fresh drops every table. Nothing may point it at a database
        // that is not a throwaway one.
        $database = config('database.connections.mysql.database');
        if (! str_ends_with($database, '_test')) {
            throw new RuntimeException('The suite only runs against a database whose name ends in _test.');
        }

        // Uploads go somewhere disposable, never into public/static.
        $uploads = storage_path("framework/testing/uploads-{$database}");
        File::deleteDirectory($uploads);
        config(['uploads.root' => $uploads]);
    }

    protected function afterTruncatingDatabase(): void
    {
        (new LookupSeeder)->run();
    }
}
