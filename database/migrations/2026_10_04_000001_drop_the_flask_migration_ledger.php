<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\Schema;

/*
 * The Flask app recorded its migrations in schema_migrations. The migration
 * before this one reads it to decide whether a database can be adopted; once
 * that has happened, the `migrations` table is the record and this one is
 * nobody's.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::dropIfExists('schema_migrations');
    }
};
