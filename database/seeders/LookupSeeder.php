<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;

/**
 * The rows the schema itself ships: the size run, so the API is usable at once,
 * and the shop's contact details, which is a single row edited in place.
 */
class LookupSeeder extends Seeder
{
    public function run(): void
    {
        DB::table('sizes')->insert([
            ['name' => 'Pequeno', 'position' => 1],
            ['name' => 'Médio', 'position' => 2],
            ['name' => 'Grande', 'position' => 3],
        ]);

        DB::table('contacts')->insert([
            'id' => 1,
            'address' => 'Viana do Castelo, Portugal',
            'email' => 'geral@coisascomgosto.pt',
            'whatsapp' => '939320334',
            'maps_url' => 'https://maps.app.goo.gl/bAYkhcE3gvaKDw5W9',
            'facebook_url' => 'https://www.facebook.com/coisascomgosto.vianadocastelo/',
            'instagram_url' => 'https://www.instagram.com/coisascomgostovc/',
        ]);
    }
}
