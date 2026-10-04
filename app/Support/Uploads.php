<?php

namespace App\Support;

use Illuminate\Http\UploadedFile;
use Illuminate\Support\Str;
use Intervention\Image\Encoders\JpegEncoder;
use Intervention\Image\Encoders\PngEncoder;
use Intervention\Image\Encoders\WebpEncoder;
use Intervention\Image\ImageManager;
use RuntimeException;
use Throwable;

/**
 * Photographs on disk, served as ordinary static files from public/static/img.
 *
 * Nothing here deletes a file except sweep(), reached only from
 * `php artisan app:sweep-uploads`. Removing a photograph in the dashboard marks
 * its row and deleting a piece removes rows; the files outlive both, because the
 * owners' only copy of a photograph may be the one they uploaded.
 */
class Uploads
{
    public const PRODUCTS = 'static/img/products';

    // Covers live apart from the pieces: a cover may point at one of the pieces'
    // own photographs, and separate folders let the sweep tell the two apart.
    public const COLLECTIONS = 'static/img/collections';

    public const MAX_BYTES = 5 * 1024 * 1024;

    // Photographs of small handmade objects; 40 megapixels is more than any of
    // them, and a 5 MB file can still decode to an enormous bitmap.
    public const MAX_PIXELS = 40_000_000;

    private const ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png', '.webp'];

    // What the file turns out to be decides the suffix, not the name it came with.
    private const FORMATS = [IMAGETYPE_JPEG => '.jpg', IMAGETYPE_PNG => '.png', IMAGETYPE_WEBP => '.webp'];

    /**
     * Stores an uploaded photograph and returns the URL it is served from.
     *
     * The bytes are decoded rather than trusted, and re-encoding is what strips
     * the metadata: the owners photograph their work at home with a phone, and a
     * phone writes the coordinates of the room into the file.
     *
     * @throws UploadError in Portuguese, naming what is wrong with the file
     */
    public static function save(?UploadedFile $file, string $folder = self::PRODUCTS): string
    {
        if ($file === null || $file->getClientOriginalName() === '') {
            throw new UploadError('Nenhum ficheiro enviado.');
        }

        $extension = strtolower(pathinfo(self::secureName($file->getClientOriginalName()), PATHINFO_EXTENSION));
        $extension = $extension === '' ? '' : ".{$extension}";
        if (! in_array($extension, self::ALLOWED_EXTENSIONS, true)) {
            throw new UploadError('Formato não suportado ('.($extension ?: 'sem extensão').'). Use '.implode(', ', self::ALLOWED_EXTENSIONS).'.');
        }

        // Cheapest rejections first: the size, then the header, then decoding.
        $size = $file->getSize();
        if ($size === 0) {
            throw new UploadError('O ficheiro está vazio.');
        }
        if ($size > self::MAX_BYTES) {
            throw new UploadError('Máximo '.intdiv(self::MAX_BYTES, 1024 * 1024).' MB.');
        }

        $header = @getimagesize($file->getRealPath());
        if ($header === false) {
            throw new UploadError('O ficheiro não é uma imagem válida.');
        }
        if (! isset(self::FORMATS[$header[2]])) {
            throw new UploadError('Formato não suportado ('.(image_type_to_extension($header[2], false) ?: 'desconhecido').'). Use '.implode(', ', self::ALLOWED_EXTENSIONS).'.');
        }
        if ($header[0] * $header[1] > self::MAX_PIXELS) {
            throw new UploadError('O ficheiro não é uma imagem válida.');
        }

        try {
            $image = ImageManager::usingDriver(\Intervention\Image\Drivers\Gd\Driver::class)->decodePath($file->getRealPath());
            $encoded = $image->encode(match ($header[2]) {
                IMAGETYPE_JPEG => new JpegEncoder(quality: 92),
                IMAGETYPE_PNG => new PngEncoder,
                IMAGETYPE_WEBP => new WebpEncoder(quality: 90),
            });
        } catch (Throwable) {
            throw new UploadError('O ficheiro não é uma imagem válida.');
        }

        $stem = mb_substr(pathinfo(self::secureName($file->getClientOriginalName()), PATHINFO_FILENAME), 0, 40) ?: 'foto';
        $name = $stem.'-'.bin2hex(random_bytes(4)).self::FORMATS[$header[2]];

        $directory = self::root()."/{$folder}";
        if (! is_dir($directory) && ! mkdir($directory, 0775, true) && ! is_dir($directory)) {
            throw new RuntimeException("Cannot create {$directory}");
        }
        $encoded->save("{$directory}/{$name}");

        return "/{$folder}/{$name}";
    }

    /**
     * Deletes the files no row points at any more, once they are older than the
     * grace period. The only unlink in the project.
     *
     * `$referenced` is every URL the database still holds, removed photographs
     * included: a removed one is restorable, so its file is still in use. The
     * age is the file's own mtime, because an upload whose request failed after
     * writing it has no row at all, and must not be raced while it is fresh.
     *
     * @return list<string> the URLs that went, or would go on a dry run
     */
    public static function sweep(array $referenced, int $olderThanDays = 30, bool $dryRun = false): array
    {
        $cutoff = time() - $olderThanDays * 86400;
        $referenced = array_flip($referenced);
        $removed = [];

        foreach ([self::PRODUCTS, self::COLLECTIONS] as $folder) {
            $directory = self::root()."/{$folder}";
            if (! is_dir($directory)) {
                continue;
            }

            $files = array_filter(scandir($directory), fn ($name) => is_file("{$directory}/{$name}"));
            sort($files);

            foreach ($files as $name) {
                $url = "/{$folder}/{$name}";
                if (isset($referenced[$url]) || filemtime("{$directory}/{$name}") > $cutoff) {
                    continue;
                }
                if (! $dryRun) {
                    unlink("{$directory}/{$name}");
                }
                $removed[] = $url;
            }
        }

        return $removed;
    }

    /** public/, or wherever the tests point `uploads.root` so they leave the repository alone. */
    private static function root(): string
    {
        return config('uploads.root') ?? public_path();
    }

    /** Werkzeug's secure_filename: ASCII, no path, nothing a shell would mind. */
    private static function secureName(string $name): string
    {
        $name = Str::ascii(basename(str_replace('\\', '/', $name)));
        $name = preg_replace('/[^A-Za-z0-9_.-]/', '', preg_replace('/\s+/', '_', $name));

        return trim($name, '._');
    }
}
