<?php

use Database\Seeders\LookupSeeder;
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/*
 * The whole catalogue as the Flask app left it at its migration 0013.
 *
 * Column types are the old ones on purpose (signed INT ids, not BIGINT): a
 * database built here and the one already in use must be the same shape, or a
 * foreign key added later works on one and fails on the other.
 *
 * The cascades are written twice: every FOREIGN KEY below states what the models
 * already do on delete, so a DELETE that bypasses them fails or cascades
 * correctly instead of leaving orphans.
 */
return new class extends Migration
{
    public function up(): void
    {
        // The database in use was built by the Flask app and already has all of
        // this. Adopt it rather than build it, but only if it reached the last
        // Flask migration: anything older is a schema these models do not match.
        if (Schema::hasTable('products')) {
            $last = DB::table('schema_migrations')
                ->where('filename', '0013_a_collection_reaches_a_piece_through_its_colours.sql')
                ->exists();

            if (! $last) {
                throw new RuntimeException('This database predates the Flask migration 0013. Bring it up to date with the Flask app before adopting it.');
            }

            return;
        }

        Schema::create('materials', function (Blueprint $table) {
            $table->integer('id', true);
            $table->string('name', 100)->unique('name');
        });

        // image_url is the cover the owners chose. Which photograph speaks for a
        // collection is an editorial decision, not the first row of a query.
        Schema::create('collections', function (Blueprint $table) {
            $table->integer('id', true);
            $table->string('name', 120)->unique('name');
            $table->text('description')->nullable();
            $table->string('image_url', 500)->nullable();
            $table->dateTime('created_at')->useCurrent();
        });

        Schema::create('colors', function (Blueprint $table) {
            $table->integer('id', true);
            $table->string('name', 80)->unique('name');
            $table->string('hex', 9)->nullable();
        });

        Schema::create('sizes', function (Blueprint $table) {
            $table->integer('id', true);
            $table->string('name', 40)->unique('name');
            $table->integer('position')->default(0);
        });

        // Flat: the shape lives in the product's own name ("Caixa rectangular").
        Schema::create('product_types', function (Blueprint $table) {
            $table->integer('id', true);
            $table->string('name', 120)->unique('name');
            $table->text('description')->nullable();
            $table->string('icon', 60)->nullable();
        });

        // Named once and shared: the collections it appears in are a join.
        Schema::create('color_sets', function (Blueprint $table) {
            $table->integer('id', true);
            $table->string('name', 120)->unique('uq_color_sets_name');
            $table->dateTime('created_at')->useCurrent();
        });

        Schema::create('collection_color_sets', function (Blueprint $table) {
            $table->integer('collection_id');
            $table->integer('color_set_id');
            $table->primary(['collection_id', 'color_set_id']);
            $table->index('color_set_id', 'idx_collection_color_sets_set');
            $table->foreign('collection_id', 'fk_collection_color_sets_collection')
                ->references('id')->on('collections')->cascadeOnDelete();
            $table->foreign('color_set_id', 'fk_collection_color_sets_set')
                ->references('id')->on('color_sets')->cascadeOnDelete();
        });

        Schema::create('color_set_colors', function (Blueprint $table) {
            $table->integer('color_set_id');
            $table->integer('color_id');
            $table->integer('position')->default(0);
            $table->primary(['color_set_id', 'color_id']);
            $table->index('color_id', 'idx_color_set_colors_color');
            $table->foreign('color_set_id', 'fk_color_set_colors_set')
                ->references('id')->on('color_sets')->cascadeOnDelete();
            $table->foreign('color_id', 'fk_color_set_colors_color')
                ->references('id')->on('colors')->cascadeOnDelete();
        });

        // A collection reaches a piece through the piece's colour sets, never
        // through a column of its own.
        Schema::create('products', function (Blueprint $table) {
            $table->integer('id', true);
            $table->integer('type_id');
            $table->integer('default_size_id')->nullable();
            $table->string('name', 180);
            $table->text('description')->nullable();
            $table->dateTime('created_at')->useCurrent();
            $table->index('type_id', 'idx_products_type');
            $table->index('default_size_id', 'idx_products_default_size');
            $table->index('name', 'idx_products_name');
            $table->index('created_at', 'idx_products_created');
            // RESTRICT: type_id is NOT NULL, so there is no unfiled state to
            // fall back on.
            $table->foreign('type_id', 'fk_products_type')
                ->references('id')->on('product_types')->restrictOnDelete();
            $table->foreign('default_size_id', 'fk_products_default_size')
                ->references('id')->on('sizes')->nullOnDelete();
        });

        Schema::create('product_variants', function (Blueprint $table) {
            $table->integer('id', true);
            $table->integer('product_id');
            $table->integer('color_set_id');
            $table->dateTime('created_at')->useCurrent();
            $table->unique(['product_id', 'color_set_id'], 'uq_product_variants_product_color_set');
            $table->index('product_id', 'idx_product_variants_product');
            $table->index('color_set_id', 'idx_product_variants_color_set');
            $table->foreign('product_id', 'fk_product_variants_product')
                ->references('id')->on('products')->cascadeOnDelete();
            $table->foreign('color_set_id', 'fk_product_variants_color_set')
                ->references('id')->on('color_sets')->cascadeOnDelete();
        });

        // Every photograph belongs to a colour, because the piece looks different
        // in each. deleted_at marks a removed one and leaves the file alone: the
        // owners' only copy of a photograph may be the one they uploaded.
        Schema::create('product_images', function (Blueprint $table) {
            $table->integer('id', true);
            $table->integer('product_id');
            $table->integer('variant_id');
            $table->string('url', 500);
            $table->string('alt', 255)->nullable();
            $table->integer('position')->default(0);
            $table->dateTime('deleted_at')->nullable();
            $table->dateTime('created_at')->useCurrent();
            $table->index('product_id', 'idx_product_images_product');
            $table->index('variant_id', 'idx_product_images_variant');
            $table->index('deleted_at', 'idx_product_images_deleted');
            $table->foreign('product_id', 'fk_product_images_product')
                ->references('id')->on('products')->cascadeOnDelete();
            $table->foreign('variant_id', 'fk_product_images_variant')
                ->references('id')->on('product_variants')->cascadeOnDelete();
        });

        // A piece may mix materials: a wooden base with a figure of modelling
        // paste. No row means nobody has classified it.
        Schema::create('product_materials', function (Blueprint $table) {
            $table->integer('product_id');
            $table->integer('material_id');
            $table->primary(['product_id', 'material_id']);
            $table->index('material_id', 'idx_product_materials_material');
            $table->foreign('product_id', 'fk_product_materials_product')
                ->references('id')->on('products')->cascadeOnDelete();
            $table->foreign('material_id', 'fk_product_materials_material')
                ->references('id')->on('materials')->cascadeOnDelete();
        });

        // Empty means "only the default size".
        Schema::create('product_sizes', function (Blueprint $table) {
            $table->integer('product_id');
            $table->integer('size_id');
            $table->primary(['product_id', 'size_id']);
            $table->index('size_id', 'idx_product_sizes_size');
            $table->foreign('product_id', 'fk_product_sizes_product')
                ->references('id')->on('products')->cascadeOnDelete();
            $table->foreign('size_id', 'fk_product_sizes_size')
                ->references('id')->on('sizes')->cascadeOnDelete();
        });

        Schema::create('users', function (Blueprint $table) {
            $table->integer('id', true);
            $table->string('username', 80)->unique('username');
            $table->string('email', 190)->unique('email');
            $table->string('password', 255);
            $table->dateTime('created_at')->nullable()->useCurrent();
        });

        // A singleton: one row, always id 1. The WhatsApp number is the phone
        // number, so there is no separate phone column.
        Schema::create('contacts', function (Blueprint $table) {
            $table->integer('id')->primary();
            $table->string('address', 255)->nullable();
            $table->string('email', 190)->nullable();
            $table->string('whatsapp', 40)->nullable();
            $table->string('maps_url', 500)->nullable();
            $table->string('facebook_url', 500)->nullable();
            $table->string('instagram_url', 500)->nullable();
        });
        DB::statement('ALTER TABLE contacts ADD CONSTRAINT chk_contacts_singleton CHECK (id = 1)');

        Schema::create('events', function (Blueprint $table) {
            $table->integer('id', true);
            $table->string('name', 180);
            $table->string('location', 180)->nullable();
            $table->text('description')->nullable();
            $table->date('starts_on');
            $table->date('ends_on')->nullable();
            $table->string('url', 500)->nullable();
            $table->index('starts_on', 'idx_events_starts_on');
        });

        // What visitors do on the storefront. No identifiers, by design: no IP,
        // no user agent, no cookie, and no column that could hold one.
        Schema::create('storefront_events', function (Blueprint $table) {
            $table->bigInteger('id', true);
            $table->string('kind', 16);
            $table->integer('product_id')->nullable();
            $table->integer('variant_id')->nullable();
            $table->integer('size_id')->nullable();
            $table->string('facet', 20)->nullable();
            $table->string('facet_label', 120)->nullable();
            $table->string('term', 120)->nullable();
            $table->integer('results')->nullable();
            $table->dateTime('created_at')->useCurrent();
            $table->index(['kind', 'created_at'], 'idx_storefront_events_kind_time');
            $table->index(['product_id', 'created_at'], 'idx_storefront_events_product');
            $table->foreign('product_id', 'fk_storefront_events_product')
                ->references('id')->on('products')->cascadeOnDelete();
            $table->foreign('variant_id', 'fk_storefront_events_variant')
                ->references('id')->on('product_variants')->nullOnDelete();
            $table->foreign('size_id', 'fk_storefront_events_size')
                ->references('id')->on('sizes')->nullOnDelete();
        });

        (new LookupSeeder)->run();
    }
};
