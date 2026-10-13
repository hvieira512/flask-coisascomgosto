<?php

namespace Database\Seeders;

use App\Models\Collection;
use App\Models\Color;
use App\Models\ColorSet;
use App\Models\Contact;
use App\Models\Event;
use App\Models\Material;
use App\Models\Product;
use App\Models\ProductImage;
use App\Models\ProductType;
use App\Models\ProductVariant;
use App\Models\Size;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;

/**
 * Development data, built from the workshop's own Facebook page (August 2026):
 * the page description, the cover montage, the photo grid and the Agonia fair
 * reels. The collections are the three motif families the page names itself.
 *
 * Re-runnable: it empties the catalogue first. Accounts are left alone.
 *
 *     php artisan db:seed
 */
class DatabaseSeeder extends Seeder
{
    private const CATALOGUE_TABLES = [
        'product_images', 'product_sizes', 'product_materials', 'product_variants', 'products',
        'collection_color_sets', 'color_set_colors', 'color_sets', 'colors',
        'product_types', 'collections', 'materials', 'events',
    ];

    private const MATERIALS = ['Madeira', 'Tecido', 'Pasta de modelar'];

    // Every piece is wood except these. Manel e Maria's heart is cut from wood
    // and the two figures are modelled.
    private const MIXED_MATERIALS = ['Manel e Maria' => ['Madeira', 'Pasta de modelar']];

    private const COLORS = [
        'Branco' => '#F5F3EF', 'Preto' => '#1B1A18', 'Dourado' => '#C9A227',
        'Vermelho' => '#B3282D', 'Azul' => '#2C5FA8', 'Azul-marinho' => '#1F2A44',
        'Verde' => '#2E6B4F', 'Prateado' => '#C9CBD1', 'Rosa' => '#D4788F', 'Castanho' => '#8A6A4F',
    ];

    private const COLLECTIONS = [
        'Filigrana' => 'Os volutas e corações da filigrana de Viana, desenhados a pincel sobre a madeira.',
        'Bordados' => 'Os motivos dos bordados de Viana, passados para peças de madeira e bastidores.',
        'Lenços' => 'As flores e as cores dos Lenços dos Namorados.',
    ];

    // name => [colours in order, the collections it appears in]. A set is named
    // once and shared, so "Preto e Branco" is the same combination in Filigrana
    // and in Bordados.
    private const COLOR_SETS = [
        'Branco e Dourado' => [['Branco', 'Dourado'], ['Filigrana', 'Bordados']],
        'Preto e Dourado' => [['Preto', 'Dourado'], ['Filigrana']],
        'Preto e Branco' => [['Preto', 'Branco'], ['Filigrana', 'Bordados']],
        'Vermelho e Branco' => [['Vermelho', 'Branco'], ['Filigrana']],
        'Azul e Branco' => [['Azul', 'Branco'], ['Filigrana', 'Bordados']],
        'Verde e Dourado' => [['Verde', 'Dourado'], ['Bordados']],
        'Preto Floral' => [['Preto', 'Vermelho', 'Verde'], ['Lenços']],
        'Vermelho Floral' => [['Vermelho', 'Branco', 'Verde'], ['Lenços']],
        'Azul-marinho e Dourado' => [['Azul-marinho', 'Dourado'], ['Filigrana']],
        'Branco e Prateado' => [['Branco', 'Prateado'], ['Filigrana']],
        'Branco e Rosa' => [['Branco', 'Rosa'], ['Filigrana']],
        'Dourado e Vermelho' => [['Dourado', 'Vermelho'], ['Filigrana']],
        'Rosa e Castanho' => [['Rosa', 'Castanho'], ['Bordados']],
        'Branco Floral' => [['Branco', 'Vermelho', 'Verde'], ['Lenços']],
    ];

    // name => [icon, description]
    private const PRODUCT_TYPES = [
        'Caixa' => ['fa-box', 'Caixas de madeira pintadas à mão, de guardar joias, missangas ou recordações.'],
        'Coração' => ['fa-heart', 'O coração de Viana recortado em madeira, de pendurar ou de pé.'],
        'Moldura' => ['fa-image', 'Molduras de fotografia com janela recta ou oval.'],
        'Bastidor' => ['fa-circle-notch', 'O bastidor de bordar, pintado ou com letras à mão.'],
        'Enfeite de Natal' => ['fa-gift', 'Enfeites de árvore, personalizados com o nome.'],
        'Presépio Minhoto' => ['fa-star', 'O presépio em traje minhoto — Manel e Maria sobre uma base recortada.'],
        'Abre-cápsulas' => ['fa-wine-bottle', 'Abre-cápsulas de madeira com pega decorada.'],
    ];

    // name => [type, description, colour sets, sizes]
    private const PRODUCTS = [
        'Caixa Redonda Filigrana' => ['Caixa', 'Caixa redonda com a filigrana desenhada a pincel na tampa.',
            ['Branco e Dourado', 'Preto e Dourado', 'Preto e Branco', 'Vermelho e Branco', 'Azul e Branco'], ['Pequeno', 'Médio', 'Grande']],
        'Manel e Maria' => ['Presépio Minhoto', 'Presépio minhoto: Manel e Maria em traje sobre um coração dourado.',
            ['Vermelho e Branco', 'Preto e Branco', 'Dourado e Vermelho'], ['Médio']],
        'Caixa de Joias' => ['Caixa', 'Caixa rectangular forrada, para joias e missangas.',
            ['Branco e Dourado', 'Preto e Dourado', 'Vermelho e Branco'], ['Pequeno', 'Médio', 'Grande']],
        'Caixa Lenço dos Namorados' => ['Caixa', 'Tampa com as flores do Lenço dos Namorados.',
            ['Preto Floral', 'Vermelho Floral', 'Branco Floral'], ['Médio']],
        'Caixa de Garrafa' => ['Caixa', 'Caixa alta para uma garrafa, decorada nas quatro faces.',
            ['Preto e Dourado', 'Azul e Branco'], []],
        'Coração de Viana' => ['Coração', 'Coração recortado em madeira, com fita para pendurar.',
            ['Branco e Dourado', 'Preto e Dourado', 'Azul e Branco', 'Vermelho e Branco'], ['Pequeno', 'Médio']],
        'Coração de Mesa' => ['Coração', 'Coração assente numa base, para ficar de pé.',
            ['Branco e Dourado', 'Preto e Branco'], ['Médio']],
        'Moldura Filigrana' => ['Moldura', 'Moldura de fotografia com filigrana à volta da janela.',
            ['Branco e Dourado', 'Preto e Dourado', 'Vermelho e Branco', 'Branco e Prateado'], ['Pequeno', 'Médio', 'Grande']],
        'Moldura Oval' => ['Moldura', 'Janela oval, com o motivo a subir pelos lados.',
            ['Branco e Dourado', 'Preto e Dourado', 'Branco e Rosa'], ['Médio']],
        'Bastidor Viana é Amor' => ['Bastidor', 'Bastidor com letras desenhadas à mão e a filigrana à volta.',
            ['Branco e Dourado', 'Azul e Branco'], ['Médio']],
        'Bastidor Bordado' => ['Bastidor', 'Bastidor com os motivos dos bordados de Viana.',
            ['Azul e Branco', 'Verde e Dourado', 'Rosa e Castanho'], ['Pequeno', 'Médio']],
        'Coração de Natal' => ['Enfeite de Natal', 'Enfeite de árvore em coração, personalizado com o nome.',
            ['Vermelho e Branco', 'Branco e Dourado'], ['Pequeno']],
        'Bola de Natal' => ['Enfeite de Natal', 'Enfeite de árvore em bola achatada, personalizado com o nome.',
            ['Vermelho e Branco', 'Branco e Dourado', 'Azul-marinho e Dourado'], ['Pequeno']],
        'Abre-cápsulas Coração' => ['Abre-cápsulas', 'Abre-cápsulas com pega em coração.',
            ['Preto e Dourado', 'Preto e Branco'], []],
    ];

    // [piece, colour set, file, alt]: photographs from the page's own albums,
    // cropped square. Every one names the colour it shows.
    private const IMAGES = [
        ['Caixa Redonda Filigrana', 'Branco e Dourado', 'caixa-redonda-dourado.jpg', 'Caixa redonda branca com coração de filigrana a dourado'],
        ['Caixa Redonda Filigrana', 'Azul e Branco', 'caixa-redonda-azul.jpg', 'Três caixas redondas brancas com filigrana azul'],
        ['Caixa Redonda Filigrana', 'Preto e Branco', 'caixa-preto-branco.jpg', 'Caixa redonda preta com filigrana branca'],
        ['Caixa Redonda Filigrana', 'Vermelho e Branco', 'caixa-coracao-vermelho.jpg', 'Caixa vermelha em forma de coração com filigrana dourada'],
        ['Manel e Maria', 'Dourado e Vermelho', 'manel-e-maria.jpg', 'O par do Minho em traje sobre um coração dourado'],
        ['Caixa de Joias', 'Preto e Dourado', 'caixa-preto-dourado.jpg', 'Peças pretas com filigrana dourada'],
        ['Moldura Oval', 'Branco e Rosa', 'moldura-rosa.jpg', 'Moldura branca de janela oval com filigrana rosa'],
        ['Bastidor Bordado', 'Rosa e Castanho', 'bastidor-nome.jpg', 'Bastidor bordado à mão com um nome ao centro'],
        ['Coração de Natal', 'Branco e Dourado', 'coracao-natal-nome.jpg', 'Coração de Viana branco com nome escrito a dourado'],
        ['Abre-cápsulas Coração', 'Preto e Dourado', 'abre-capsulas.jpg', 'Três abre-cápsulas de madeira com motivos pintados'],
        ['Caixa Lenço dos Namorados', 'Branco Floral', 'caixa-lenco-rosas.jpg', 'Caixa branca com as rosas do Lenço dos Namorados na tampa'],
        ['Coração de Viana', 'Branco e Dourado', 'coracao-branco-nome.jpg', 'Coração de Viana branco com nome escrito a dourado'],
        ['Coração de Viana', 'Vermelho e Branco', 'coracao-vermelho-nome.jpg', 'Coração de Viana vermelho com letras douradas'],
        ['Coração de Mesa', 'Branco e Dourado', 'coracao-mesa-figura.jpg', 'Coração de pé com uma figura em traje minhoto'],
        ['Coração de Mesa', 'Branco e Dourado', 'coracao-mesa-par.jpg', 'Coração de pé com o par do Minho e a frase quem ama fica'],
        ['Moldura Filigrana', 'Branco e Prateado', 'moldura-branco.jpg', 'Moldura branca com filigrana prateada'],
        ['Moldura Filigrana', 'Preto e Dourado', 'moldura-preto-dourado.jpg', 'Moldura preta com janela oval e filigrana dourada'],
        ['Bastidor Viana é Amor', 'Branco e Dourado', 'bastidor-dourado.jpg', 'Bastidor com um coração de Viana bordado a dourado'],
        ['Bastidor Viana é Amor', 'Azul e Branco', 'bastidor-azul-nome.jpg', 'Bastidor com coração bordado a azul e um nome'],
        ['Bola de Natal', 'Branco e Dourado', 'bola-natal-branco.jpg', 'Bastidor branco com coração dourado e laço vermelho'],
        ['Bola de Natal', 'Vermelho e Branco', 'bola-natal-vermelho.jpg', 'Três bastidores vermelhos com filigrana branca'],
        ['Bola de Natal', 'Azul-marinho e Dourado', 'bola-natal-azul.jpg', 'Bastidor azul-escuro com coração dourado, pendurado na árvore'],
        ['Coração de Natal', 'Vermelho e Branco', 'coracao-natal-branco.jpg', 'Coração de Viana branco com nome, na árvore'],
    ];

    private const CONTACT = [
        'address' => 'Rua de Cardielos, n. 222, Viana do Castelo',
        'email' => 'geral@coisascomgosto.pt',
        'whatsapp' => '939320334',
        'maps_url' => 'https://maps.app.goo.gl/bAYkhcE3gvaKDw5W9',
        'facebook_url' => 'https://www.facebook.com/coisascomgosto.vianadocastelo/',
        'instagram_url' => 'https://www.instagram.com/coisascomgosto.vianadocastelo/',
    ];

    public function run(): void
    {
        // TRUNCATE rather than DELETE, so the catalogue gets the same ids every
        // time; MySQL refuses it on a table a foreign key points at unless the
        // checks are off. `users` is not on the list.
        DB::statement('SET FOREIGN_KEY_CHECKS = 0');
        try {
            foreach (self::CATALOGUE_TABLES as $table) {
                DB::table($table)->truncate();
            }
        } finally {
            DB::statement('SET FOREIGN_KEY_CHECKS = 1');
        }

        $materials = collect(self::MATERIALS)->mapWithKeys(fn ($name) => [$name => Material::create(['name' => $name])->id]);
        $colors = collect(self::COLORS)->map(fn ($hex, $name) => Color::create(['name' => $name, 'hex' => $hex])->id);
        $collections = collect(self::COLLECTIONS)->map(fn ($description, $name) => Collection::create(['name' => $name, 'description' => $description])->id);

        $sets = collect(self::COLOR_SETS)->map(function ($spec, $name) use ($colors, $collections) {
            [$colorNames, $collectionNames] = $spec;
            $set = ColorSet::create(['name' => $name]);
            $set->setColors(array_map(fn ($c) => $colors[$c], $colorNames));
            $set->collections()->sync(array_map(fn ($c) => $collections[$c], $collectionNames));

            return $set->id;
        });

        $types = collect(self::PRODUCT_TYPES)->map(fn ($spec, $name) => ProductType::create(['name' => $name, 'icon' => $spec[0], 'description' => $spec[1]])->id);
        $sizes = Size::pluck('id', 'name');

        $products = [];
        $variants = [];
        foreach (self::PRODUCTS as $name => [$type, $description, $setNames, $sizeNames]) {
            $product = Product::create(['name' => $name, 'type_id' => $types[$type], 'description' => $description]);
            $products[$name] = $product->id;
            $product->materials()->sync(array_map(fn ($m) => $materials[$m], self::MIXED_MATERIALS[$name] ?? ['Madeira']));
            foreach ($setNames as $setName) {
                $variants[$name][$setName] = ProductVariant::create(['product_id' => $product->id, 'color_set_id' => $sets[$setName]])->id;
            }
            $product->sizes()->sync(array_values(array_filter(array_map(fn ($s) => $sizes[$s] ?? null, $sizeNames))));
        }

        $positions = [];
        foreach (self::IMAGES as [$piece, $setName, $file, $alt]) {
            $positions[$piece] = ($positions[$piece] ?? 0) + 1;
            // Indexed rather than defaulted: a photograph naming a colour the
            // piece is not offered in is a mistake in the tables above.
            ProductImage::create([
                'product_id' => $products[$piece],
                'variant_id' => $variants[$piece][$setName],
                'url' => "/static/img/products/{$file}",
                'alt' => $alt,
                'position' => $positions[$piece],
            ]);
        }

        Event::create([
            'name' => "XXIV Exposição/Feira de Artesanato da Romaria d'Agonia",
            'location' => 'Jardim Público, Viana do Castelo',
            'description' => 'Cerca de 50 expositores, dezassete dias de feira no jardim.',
            'starts_on' => '2026-08-07',
            'ends_on' => '2026-08-23',
            'url' => 'https://www.facebook.com/coisascomgosto.vianadocastelo/',
        ]);

        Contact::updateOrCreate(['id' => 1], self::CONTACT);

        $this->command?->info(sprintf('Seeded %d products, %d product types, %d colour sets, %d images, 1 event.',
            count(self::PRODUCTS), count(self::PRODUCT_TYPES), count(self::COLOR_SETS), count(self::IMAGES)));
    }
}
