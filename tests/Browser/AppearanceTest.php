<?php

use Database\Seeders\DatabaseSeeder;
use Illuminate\Support\Facades\DB;

/*
 * What the pages look like, compared against committed baselines.
 *
 * The rest of the suite tests geometry and never appearance, and the difference
 * has cost real defects: a modal card that rendered transparent, colour-set
 * names invisible because a line-height collapsed them, photo slots at three
 * times their size. Every one was found by eye, on a screenshot, after the tests
 * had gone green.
 *
 * Each page is captured at two widths, downscaled, and compared with the
 * baseline in tests/baselines/. Downscaled on purpose: a full-resolution
 * comparison fails on font anti-aliasing, while a thumbnail still fails loudly on
 * anything the eye would notice — a missing background, collapsed padding, text
 * the colour of the paper.
 *
 * Off unless asked for. Chromium renders text differently on macOS and on Linux,
 * so a baseline captured on one fails on the other, and CI does not run this:
 *
 *     SCREENSHOTS=1 vendor/bin/pest tests/Browser/AppearanceTest.php        compare
 *     SCREENSHOTS=update vendor/bin/pest tests/Browser/AppearanceTest.php   recapture
 */

const APPEARANCE_PAGES = [
    'store-home' => ['/', false],
    'store-catalogue' => ['/products', false],
    'store-product' => ['/products/1', false],
    'auth' => ['/auth', false],
    'dash-home' => ['/dashboard/home', true],
    'dash-products' => ['/dashboard/products', true],
    'dash-types' => ['/dashboard/types', true],
    'dash-colors' => ['/dashboard/colors', true],
    'dash-collections' => ['/dashboard/collections', true],
    'dash-events' => ['/dashboard/events', true],
    'dash-contacts' => ['/dashboard/contacts', true],
];

const APPEARANCE_WIDTHS = ['desktop' => 1280, 'phone' => 390];

// About a thumbnail: where a human notices "that band of colour is gone" and not
// that a glyph is a shade darker.
const APPEARANCE_COMPARE_WIDTH = 240;

// The fold and a good way past it; what is further down is where the geometry
// tests do their work, and full-length baselines would bloat the repository.
const APPEARANCE_MAX_HEIGHT = 1400;

// Per-channel distance that counts as a real difference rather than rendering
// noise, and how much of the page may differ before it is a failure.
const APPEARANCE_CHANNEL_DELTA = 24;
const APPEARANCE_ALLOWED_FRACTION = 0.001;

beforeEach(function () {
    if (! in_array(getenv('SCREENSHOTS'), ['1', 'update'], true)) {
        $this->markTestSkipped('Appearance tests are opt-in: SCREENSHOTS=1 to compare, SCREENSHOTS=update to recapture.');
    }

    // The seeded catalogue — fourteen pieces with their real photographs — is
    // what makes a pixel comparison meaningful at all.
    (new DatabaseSeeder)->run();
});

/** The capture scaled down and cropped to the compared region. */
function appearanceShrink(string $png): GdImage
{
    $image = imagecreatefromstring($png);
    if (imagesx($image) > APPEARANCE_COMPARE_WIDTH) {
        // Triangle averages every source pixel into the result; GD's bicubic
        // refuses a downscale this steep.
        $image = imagescale($image, APPEARANCE_COMPARE_WIDTH, -1, IMG_TRIANGLE);
    }
    if (imagesy($image) > APPEARANCE_MAX_HEIGHT) {
        $image = imagecrop($image, ['x' => 0, 'y' => 0, 'width' => imagesx($image), 'height' => APPEARANCE_MAX_HEIGHT]);
    }

    return $image;
}

/** The fraction of pixels that differ by more than the noise floor. */
function appearanceDifference(GdImage $actual, GdImage $baseline): float
{
    [$width, $height] = [imagesx($actual), imagesy($actual)];
    if ($width !== imagesx($baseline) || $height !== imagesy($baseline)) {
        return 1.0;
    }

    $differing = 0;
    for ($y = 0; $y < $height; $y++) {
        for ($x = 0; $x < $width; $x++) {
            $a = imagecolorat($actual, $x, $y);
            $b = imagecolorat($baseline, $x, $y);
            foreach ([16, 8, 0] as $shift) {
                if (abs((($a >> $shift) & 0xFF) - (($b >> $shift) & 0xFF)) > APPEARANCE_CHANNEL_DELTA) {
                    $differing++;
                    break;
                }
            }
        }
    }

    return $differing / ($width * $height);
}

it('looks the way it did', function (string $name, string $label) {
    [$path, $signedIn] = APPEARANCE_PAGES[$name];

    if ($signedIn) {
        // Opening a piece records a view, and a dashboard home saying "a contar
        // desde <today>" fails tomorrow.
        DB::table('storefront_events')->delete();
        signIn(makeUser('shots'));
    }

    $page = visit($path, [
        'viewport' => ['width' => APPEARANCE_WIDTHS[$label], 'height' => 900],
        // A fixed ratio, or a retina machine and a normal one disagree on every pixel.
        'deviceScaleFactor' => 1,
        'reducedMotion' => 'reduce',
    ]);
    // The pages render their content from the API, the loader stays over them
    // until the last photograph is in, and Font Awesome's kit registers its
    // faces late and only then fetches the one in use. A fixed pause caught
    // text under the fading loader, drawn a shade differently, and buttons
    // without their icons; this waits for the page to settle, then for the fades.
    $settled = "!document.getElementById('page-loader')"
        ." && !document.querySelector('.placeholder')"
        .' && [...document.images].every((image) => image.complete)'
        .' && [...document.fonts].some((face) => /Font Awesome/.test(face.family))'
        ." && document.fonts.status === 'loaded'";
    waitUntil($page, $settled);
    $page->wait(0.5);

    $file = "appearance-{$name}-{$label}";
    $page->screenshot(fullPage: true, filename: $file);
    $actual = appearanceShrink(file_get_contents(base_path("tests/Browser/Screenshots/{$file}.png")));

    $baseline = base_path("tests/baselines/{$name}-{$label}.png");
    if (getenv('SCREENSHOTS') === 'update') {
        imagepng($actual, $baseline);
        $this->markTestSkipped("captured {$name}-{$label}.png");
    }

    expect(is_file($baseline))->toBeTrue("No baseline for {$name}-{$label}. Run with SCREENSHOTS=update.");

    $fraction = appearanceDifference($actual, imagecreatefrompng($baseline));
    expect($fraction)->toBeLessThanOrEqual(APPEARANCE_ALLOWED_FRACTION,
        sprintf('%s at %s differs from its baseline in %.2f%% of pixels. Captured: tests/Browser/Screenshots/%s.png', $name, $label, $fraction * 100, $file));
})->with(array_keys(APPEARANCE_PAGES))->with(array_keys(APPEARANCE_WIDTHS));
