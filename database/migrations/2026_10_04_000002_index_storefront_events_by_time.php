<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/*
 * The dashboard's totals and daily series ask "every event since this date",
 * whatever its kind. Neither existing index leads with created_at, so MySQL
 * read the whole of a table that only ever grows.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('storefront_events', function (Blueprint $table) {
            $table->index('created_at', 'idx_storefront_events_time');
        });
    }
};
