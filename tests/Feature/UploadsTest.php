<?php

use App\Models\ProductImage;
use App\Support\Uploads;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Log;
use Illuminate\Testing\TestResponse;

beforeEach(fn () => signIn());

/** A product with one colour on it: every photograph belongs to one. */
function uploadsProduct(): array
{
    $product = makeProduct('Caixa');
    $variant = makeVariant($product, makeColorSet('Branco', [makeColor('Branco', '#F5F3EF')['id']]));

    return [...$product, 'variant_id' => $variant['id']];
}

/** `variant_id` defaults to the product's own colour. */
function uploadsPost(array $product, ?UploadedFile $file = null, array $form = []): TestResponse
{
    return test()->post("/api/products/{$product['id']}/images/upload", [
        'file' => $file ?? photo('foto.jpg'),
        'variant_id' => (string) $product['variant_id'],
        ...$form,
    ]);
}

function uploadsDir(): string
{
    return config('uploads.root').'/'.Uploads::PRODUCTS;
}

function uploadsPathOf(string $url): string
{
    return uploadsDir().'/'.basename($url);
}

/** Nothing may reach the disk. */
function uploadsNothingStored(): void
{
    expect(is_dir(uploadsDir()) ? array_diff(scandir(uploadsDir()), ['.', '..']) : [])->toBe([]);
}

function uploadsFile(string $name, string $content): UploadedFile
{
    return UploadedFile::fake()->createWithContent($name, $content);
}

function uploadsBytes(UploadedFile $file): string
{
    return file_get_contents($file->getRealPath());
}

/**
 * A JPEG carrying what a phone attaches: the make, and a GPS block. GD cannot
 * write EXIF, so the APP1 segment is spliced in after the SOI marker by hand.
 */
function uploadsPhoneJpeg(int $width = 40, int $height = 30): string
{
    $entry = fn (int $tag, int $type, int $count, string $value) => pack('vvV', $tag, $type, $count).str_pad($value, 4, "\0");

    // IFD0 at 8: two entries, then Make's string at 38 and the GPS IFD at 48.
    $tiff = "II*\0".pack('V', 8)
        .pack('v', 2)
        .$entry(0x010F, 2, 10, pack('V', 38))
        .$entry(0x8825, 4, 1, pack('V', 48))
        .pack('V', 0)
        ."TestPhone\0"
        .pack('v', 1)
        .$entry(0x0001, 2, 2, "N\0")
        .pack('V', 0);
    $app1 = "Exif\0\0".$tiff;
    $jpeg = uploadsBytes(photo('foto.jpg', 'jpeg', $width, $height));

    return substr($jpeg, 0, 2)."\xFF\xE1".pack('n', strlen($app1) + 2).$app1.substr($jpeg, 2);
}

/** A PNG whose header claims far more pixels than its few bytes hold. */
function uploadsBombPng(int $width = 10_000, int $height = 10_000): string
{
    $chunk = fn (string $type, string $data) => pack('N', strlen($data)).$type.$data.pack('N', crc32($type.$data));

    return "\x89PNG\r\n\x1a\n"
        .$chunk('IHDR', pack('NNCCCCC', $width, $height, 8, 2, 0, 0, 0))
        .$chunk('IDAT', gzcompress(str_repeat("\0", 64)))
        .$chunk('IEND', '');
}

describe('the upload endpoint', function () {
    it('requires a token', function () {
        $product = uploadsProduct();
        Auth::forgetGuards();

        uploadsPost($product)->assertUnauthorized();
    });

    it('stores the file and attaches it', function () {
        $url = uploadsPost(uploadsProduct())->assertCreated()->json('url');

        expect($url)->toStartWith('/static/img/products/')
            ->and(uploadsPathOf($url))->toBeFile();
    });

    it('refuses a non-image', function () {
        expect(uploadsPost(uploadsProduct(), uploadsFile('notas.txt', 'olá'))->assertStatus(400)->json('message'))->toContain('suportado');
    });

    it('keeps a refused file out of the error log', function () {
        Log::spy();
        uploadsPost(uploadsProduct(), uploadsFile('notas.txt', 'olá'))->assertStatus(400);

        Log::shouldNotHaveReceived('error');
    });

    it('refuses an oversized file', function () {
        uploadsPost(uploadsProduct(), uploadsFile('foto.jpg', str_repeat('x', Uploads::MAX_BYTES + 1)))->assertStatus(400);
    });

    it('answers 404 for an unknown product', function () {
        uploadsPost(['id' => 9999, 'variant_id' => 1])->assertNotFound();
    });

    it('can be pinned to a variant', function () {
        $product = uploadsProduct();
        $variant = makeVariant($product, makeColorSet('Vermelho', [makeColor('Vermelho', '#B3282D')['id']]));

        uploadsPost($product, form: ['variant_id' => (string) $variant['id']])
            ->assertCreated()
            ->assertJsonPath('variant_id', $variant['id']);
    });

    it('answers 404 for a variant of another product', function () {
        $product = uploadsProduct();
        $other = makeProduct('Outra');
        $variant = makeVariant($other, makeColorSet('Azul', [makeColor('Azul', '#2C5FA8')['id']]));

        uploadsPost($product, form: ['variant_id' => (string) $variant['id']])->assertNotFound();
    });

    it('leaves the file when the image is deleted', function () {
        $product = uploadsProduct();
        $made = uploadsPost($product)->json();
        expect(uploadsPathOf($made['url']))->toBeFile();

        $this->deleteJson("/api/products/{$product['id']}/images/{$made['id']}");

        expect(uploadsPathOf($made['url']))->toBeFile();
    });
});

/*
 * The photographs outlive every delete. They used to be unlinked in the same
 * request, and for people whose only copy may be the one they uploaded from a
 * phone, a mis-tap was unrecoverable. Only the sweep deletes a file now.
 */
describe('no deletion touches a file', function () {
    beforeEach(function () {
        $this->product = uploadsProduct();
        $this->colorSet = makeColorSet('Vermelho', [makeColor('Vermelho', '#B3282D')['id']]);
        $this->variant = makeVariant($this->product, $this->colorSet);
    });

    it('keeps the file when a photograph is removed', function () {
        $made = uploadsPost($this->product)->json();

        $this->deleteJson("/api/products/{$this->product['id']}/images/{$made['id']}")->assertOk();

        expect(uploadsPathOf($made['url']))->toBeFile();
    });

    // Kept on disk, and kept out of sight: the surviving row must not bring it back.
    it('takes a removed photograph out of the catalogue', function () {
        $made = uploadsPost($this->product)->json();

        $this->deleteJson("/api/products/{$this->product['id']}/images/{$made['id']}");

        $this->getJson("/api/products/{$this->product['id']}/images")->assertExactJson([]);
        $this->getJson("/api/products/{$this->product['id']}")
            ->assertJsonPath('primary_image', null)
            ->assertJsonPath('variants.0.images', []);
    });

    it('cannot remove a photograph twice', function () {
        $made = uploadsPost($this->product)->json();
        $this->deleteJson("/api/products/{$this->product['id']}/images/{$made['id']}");

        $this->deleteJson("/api/products/{$this->product['id']}/images/{$made['id']}")->assertNotFound();
    });

    // There is no button for it yet; restoring the row is the whole recovery.
    it('can put a removed photograph back', function () {
        $made = uploadsPost($this->product)->json();
        $this->deleteJson("/api/products/{$this->product['id']}/images/{$made['id']}");

        ProductImage::withTrashed()->findOrFail($made['id'])->restore();

        expect($this->getJson("/api/products/{$this->product['id']}/images")->json('*.id'))->toBe([$made['id']]);
    });

    it('keeps the photographs when the piece is deleted', function () {
        $made = uploadsPost($this->product)->json();

        $this->deleteJson("/api/products/{$this->product['id']}");

        expect(uploadsPathOf($made['url']))->toBeFile();
    });

    it('keeps the photographs when a colour is dropped', function () {
        $made = uploadsPost($this->product, form: ['variant_id' => (string) $this->variant['id']])->json();

        $this->deleteJson("/api/products/{$this->product['id']}/variants/{$this->variant['id']}");

        expect(uploadsPathOf($made['url']))->toBeFile();
    });

    it('keeps the photographs when a colour set is deleted', function () {
        $made = uploadsPost($this->product, form: ['variant_id' => (string) $this->variant['id']])->json();

        $this->deleteJson("/api/color-sets/{$this->colorSet['id']}");

        expect(uploadsPathOf($made['url']))->toBeFile();
    });

    // A removed photograph of a colour that no longer exists is a state nothing
    // could present, so those rows go outright. Only the file survives.
    it('still removes the rows when the colour goes', function () {
        uploadsPost($this->product, form: ['variant_id' => (string) $this->variant['id']])->assertCreated();

        $this->deleteJson("/api/products/{$this->product['id']}/variants/{$this->variant['id']}");

        $this->getJson("/api/products/{$this->product['id']}/images")->assertExactJson([]);
    });
});

/*
 * Age is read off the file rather than a row: an upload whose request failed
 * after the file was written has no row at all, and collecting it the instant
 * it appears would race a request still running.
 */
describe('the sweep is the only thing that deletes', function () {
    function uploadsOrphan(int $ageDays = 0, string $name = 'orfa.jpg'): string
    {
        if (! is_dir(uploadsDir())) {
            mkdir(uploadsDir(), 0775, true);
        }
        $path = uploadsDir()."/{$name}";
        file_put_contents($path, uploadsBytes(photo()));
        if ($ageDays) {
            touch($path, time() - $ageDays * 86400);
        }

        return $path;
    }

    function uploadsAge(string $url, int $days): void
    {
        touch(uploadsPathOf($url), time() - $days * 86400);
    }

    it('removes a file no row points at', function () {
        $path = uploadsOrphan(40);

        expect(Uploads::sweep([], 30))->toBe(['/'.Uploads::PRODUCTS.'/'.basename($path)])
            ->and($path)->not->toBeFile();
    });

    it('leaves a referenced file however old', function () {
        $path = uploadsOrphan(400);

        Uploads::sweep(['/'.Uploads::PRODUCTS.'/'.basename($path)], 30);

        expect($path)->toBeFile();
    });

    // A photograph uploaded a moment ago has no row yet while its request runs.
    it('leaves a file inside the grace period', function () {
        $path = uploadsOrphan(1);

        Uploads::sweep([], 30);

        expect($path)->toBeFile();
    });

    it('changes nothing on a dry run', function () {
        $path = uploadsOrphan(40);

        expect(Uploads::sweep([], 30, dryRun: true))->toBe(['/'.Uploads::PRODUCTS.'/'.basename($path)])
            ->and($path)->toBeFile();
    });

    // This is what makes removal reversible: the row keeps the file alive.
    it('treats a removed photograph as referenced until its row is purged', function () {
        $product = uploadsProduct();
        $made = uploadsPost($product)->json();
        $this->deleteJson("/api/products/{$product['id']}/images/{$made['id']}");
        uploadsAge($made['url'], 400);

        $this->artisan('app:sweep-uploads', ['--days' => 30])->assertSuccessful();

        expect(uploadsPathOf($made['url']))->toBeFile();
    });

    it('frees the file once the row is purged', function () {
        $product = uploadsProduct();
        $made = uploadsPost($product)->json();
        $this->deleteJson("/api/products/{$product['id']}/images/{$made['id']}");
        uploadsAge($made['url'], 400);

        // Marked a moment ago, so nothing to purge yet at thirty days.
        $this->artisan('app:sweep-uploads', ['--days' => 30])->expectsOutputToContain('Rows purged: 0.')->assertSuccessful();
        expect(uploadsPathOf($made['url']))->toBeFile();

        $this->artisan('app:sweep-uploads', ['--days' => 0])->expectsOutputToContain('Rows purged: 1.')->assertSuccessful();
        expect(uploadsPathOf($made['url']))->not->toBeFile();
    });

    // The sweep only looks inside the two upload folders, so files placed by
    // hand cannot be collected.
    it('never reaches a seeded asset', function () {
        Uploads::sweep([], 0);

        expect(public_path('static/img/logo.png'))->toBeFile();
    });
});

describe('filename safety', function () {
    it('strips traversal from the name', function () {
        $url = uploadsPost(uploadsProduct(), photo('../../../evil.jpg'))->assertCreated()->json('url');

        expect($url)->not->toContain('..')
            ->and(dirname($url))->toBe('/static/img/products')
            ->and(uploadsPathOf($url))->toBeFile();
    });

    it('does not collide on two uploads of one name', function () {
        $product = uploadsProduct();

        expect(uploadsPost($product, photo('caixa.jpg'))->json('url'))
            ->not->toBe(uploadsPost($product, photo('caixa.jpg'))->json('url'));
    });
});

// An extension is a claim by whoever uploaded the file, so the bytes decide.
describe('what is actually in the file', function () {
    it('refuses a file that is not an image', function () {
        $response = uploadsPost(uploadsProduct(), uploadsFile('foto.jpg', "\xff\xd8\xff\xe0 fake jpeg"));

        expect($response->assertStatus(400)->json('message'))->toContain('não é uma imagem');
        uploadsNothingStored();
    });

    // A cut-off upload has a perfectly good header.
    it('refuses a truncated image', function () {
        $whole = uploadsBytes(photo('foto.jpg', 'jpeg', 200, 200));

        uploadsPost(uploadsProduct(), uploadsFile('foto.jpg', substr($whole, 0, intdiv(strlen($whole), 3))))->assertStatus(400);
        uploadsNothingStored();
    });

    // The suffix is what the browser will be told the file is when it is served.
    it('stores the suffix of the real format', function () {
        $url = uploadsPost(uploadsProduct(), uploadsFile('enganador.jpg', uploadsBytes(photo('x.png', 'png'))))->json('url');

        expect($url)->toEndWith('.png')
            ->and(getimagesize(uploadsPathOf($url))[2])->toBe(IMAGETYPE_PNG);
    });

    // Markup with a .png suffix, which a browser would otherwise be free to interpret.
    it('refuses an SVG dressed as a PNG', function () {
        $svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>';

        uploadsPost(uploadsProduct(), uploadsFile('foto.png', $svg))->assertStatus(400);
        uploadsNothingStored();
    });
});

// A phone writes the coordinates of the room into the file, and these files are
// served publicly.
describe('metadata is stripped', function () {
    it('keeps EXIF off the disk', function () {
        $original = uploadsPhoneJpeg();
        $source = uploadsFile('foto.jpg', $original);
        expect(@exif_read_data($source->getRealPath()))->toHaveKey('Make');

        $url = uploadsPost(uploadsProduct(), $source)->assertCreated()->json('url');

        $stored = file_get_contents(uploadsPathOf($url));
        expect($stored)->not->toContain("Exif\0\0")->not->toContain('TestPhone');
    });

    it('drops the GPS block in particular', function () {
        $source = uploadsFile('foto.jpg', uploadsPhoneJpeg());
        expect(@exif_read_data($source->getRealPath()))->toHaveKey('GPSLatitudeRef');

        $url = uploadsPost(uploadsProduct(), $source)->json('url');

        expect(@exif_read_data(uploadsPathOf($url)) ?: [])->not->toHaveKey('GPSLatitudeRef');
    });

    // Re-encoding must leave the picture itself intact.
    it('keeps the photograph itself', function () {
        $url = uploadsPost(uploadsProduct(), photo('foto.jpg', 'jpeg', 64, 48))->json('url');

        [$width, $height, $type] = getimagesize(uploadsPathOf($url));
        expect([$width, $height, $type])->toBe([64, 48, IMAGETYPE_JPEG]);
    });
});

describe('the decompression limit', function () {
    // A few hundred kilobytes of PNG can decode to gigabytes of bitmap, so the
    // pixel count is checked from the header, before anything is decoded.
    it('refuses a bomb rather than decoding it', function () {
        uploadsPost(uploadsProduct(), uploadsFile('foto.png', uploadsBombPng()))->assertStatus(400);
        uploadsNothingStored();
    });
});
