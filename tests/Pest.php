<?php

use App\Models\ProductType;
use App\Models\User;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Hash;
use Pest\Browser\Playwright\Playwright;
use Tests\TestCase;

pest()->extend(TestCase::class)->in('Feature', 'Browser');

/*
 * How long a browser test waits for the page to do something. Five seconds
 * is plenty on a laptop and not on a CI runner, where the server, MySQL and
 * Chromium share two cores: there, pages that render from the API took longer
 * than that and whole files failed on timeouts.
 */
const BROWSER_WAIT_SECONDS = 20;
Playwright::setTimeout(BROWSER_WAIT_SECONDS * 1000);

/**
 * Poll a JavaScript expression on the page until it is truthy. The plugin's
 * own waitFor* helpers build the request but never send it, so this polls.
 */
function waitUntil($page, string $js): void
{
    $until = microtime(true) + BROWSER_WAIT_SECONDS;
    while (! $page->script($js) && microtime(true) < $until) {
        $page->wait(0.05);
    }
    if ($page->script($js)) {
        return;
    }

    // What the page had to say for itself: a script that failed is the usual reason.
    $said = array_map(fn (array $entry) => $entry['message'], [...$page->page()->javaScriptErrors(), ...$page->page()->consoleLogs()]);
    expect(false)->toBeTrue("timed out waiting for: {$js}\nconsole: ".(implode("\n", $said) ?: '(quiet)'));
}

/*
 * Builders that go through the API, as the dashboard does, so a test reads as
 * the owners using the shop. Each asserts its own 201: a fixture that silently
 * failed would make the test after it fail for the wrong reason.
 */

/** An account, made directly: the tests of registration itself use the API. */
function makeUser(string $username = 'alice', string $password = 'Passw0rd!', ?string $email = null): User
{
    return User::create([
        'username' => $username,
        'email' => $email ?? "{$username}@example.com",
        'password' => Hash::make($password),
    ]);
}

/**
 * Signed in by session, with the header core/api.js puts on every request —
 * the dashboard behaving normally. Tests of the guard itself leave it off.
 */
function signIn(?User $user = null): User
{
    $user ??= makeUser('tokenuser');
    test()->actingAs($user)->withHeader('X-Requested-With', 'fetch');

    return $user;
}

/** The token pair an API client gets from /auth/login. */
function tokens(string $username = 'apiclient'): array
{
    makeUser($username);

    return test()->postJson('/api/auth/login', ['username' => $username, 'password' => 'Passw0rd!'])
        ->assertOk()->json();
}

function created(string $uri, array $payload): array
{
    return test()->postJson($uri, $payload)->assertCreated()->json();
}

function makeMaterial(string $name = 'Madeira'): array
{
    return created('/api/materials/', ['name' => $name]);
}

function makeColor(string $name = 'White', ?string $hex = null): array
{
    return created('/api/colors/', array_filter(['name' => $name, 'hex' => $hex]));
}

function makeCollection(string $name = 'Barra da Saia', ?string $description = null): array
{
    return created('/api/collections/', array_filter(['name' => $name, 'description' => $description]));
}

/** `$collectionIds` is a list: a set may appear in several collections, or in none. */
function makeColorSet(string $name = 'White and Green', ?array $colorIds = null, array $collectionIds = []): array
{
    $payload = ['name' => $name, 'color_ids' => $colorIds ?? [makeColor("{$name} filler")['id']]];
    if ($collectionIds) {
        $payload['collection_ids'] = $collectionIds;
    }

    return created('/api/color-sets/', $payload);
}

function makeProductType(string $name = 'Coracao', ?string $description = null, ?string $icon = null): array
{
    return created('/api/product-types/', array_filter(['name' => $name, 'description' => $description, 'icon' => $icon]));
}

/**
 * A ready-made type, for products built by hand. Not a real domain name:
 * utf8mb4_unicode_ci is accent-insensitive, so "Coracao" would collide with a
 * test creating "Coração".
 */
function productType(): array
{
    $type = ProductType::firstWhere('name', 'Tipo de teste');

    return $type ? test()->getJson("/api/product-types/{$type->id}")->json() : makeProductType('Tipo de teste');
}

function makeProduct(string $name = 'Vinho', string $description = 'Tinto', ?int $typeId = null, ?array $materialIds = null, ?int $defaultSizeId = null): array
{
    return created('/api/products/', array_filter([
        'name' => $name,
        'description' => $description,
        'type_id' => $typeId ?? productType()['id'],
        'material_ids' => $materialIds,
        'default_size_id' => $defaultSizeId,
    ], fn ($v) => $v !== null));
}

/** Offer $product in a colour set, and return the variant. */
function makeVariant(array $product, ?array $colorSet = null): array
{
    $colorSet ??= makeColorSet("Cor de {$product['name']}", [makeColor("Cor de {$product['name']} tom")['id']]);

    return created("/api/products/{$product['id']}/variants", ['color_set_id' => $colorSet['id']]);
}

/**
 * Put a piece in a collection the only way there is: offer it in a colour set
 * the collection gathers.
 */
function putInCollection(array $product, array $collection, ?string $setName = null): array
{
    $name = $setName ?? "Cor de {$product['name']}";
    $set = makeColorSet($name, [makeColor("{$name} tom")['id']], [$collection['id']]);
    makeVariant($product, $set);

    return $set;
}

/** The Pequeno / Médio / Grande rows the schema seeds, keyed by name. */
function sizes(): array
{
    return collect(test()->getJson('/api/sizes/')->json('sizes'))->keyBy('name')->all();
}

/** A real, decodable image of the given format, as an uploadable file. */
function photo(string $name = 'caixa.jpg', string $format = 'jpeg', int $width = 8, int $height = 8): UploadedFile
{
    $image = imagecreatetruecolor($width, $height);
    imagefill($image, 0, 0, imagecolorallocate($image, 200, 120, 40));
    ob_start();
    match ($format) {
        'png' => imagepng($image),
        'webp' => imagewebp($image),
        default => imagejpeg($image),
    };

    return UploadedFile::fake()->createWithContent($name, ob_get_clean());
}
