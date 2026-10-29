<?php

/*
 * The product page's gallery. Every photograph belongs to a colour; a colour
 * with none draws its placeholder rather than borrowing another's.
 */

beforeEach(fn () => signIn());

function galleryUpload(array $product, array $variant, string $name = 'foto.jpg'): void
{
    test()->post("/api/products/{$product['id']}/images/upload", ['file' => photo($name), 'variant_id' => (string) $variant['id']])
        ->assertCreated();
}

function galleryOption(string $title): string
{
    return ".variant-option[title=\"{$title}\"]";
}

function galleryBox($page, string $selector): ?array
{
    return $page->script("(() => { const el = document.querySelector('{$selector}'); if (!el.getClientRects().length) return null; const b = el.getBoundingClientRect(); return {x: b.x, y: b.y, width: b.width, height: b.height}; })()");
}

/**
 * Two colours: one photographed twice, one not at all. Two photographs give the
 * strip something to preview, and a colour with none is half the catalogue.
 */
function galleryPiece(): array
{
    $product = makeProduct('Coração de Mesa');
    $white = makeColor('Branco', '#FFFFFF');
    $gold = makeColor('Dourado', '#C8A24B');
    $photographed = makeVariant($product, makeColorSet('Branco e Dourado', [$white['id'], $gold['id']]));
    makeVariant($product, makeColorSet('Preto e Branco', [$white['id']]));

    galleryUpload($product, $photographed);
    galleryUpload($product, $photographed);

    return $product;
}

function galleryOpen(array $product, int $width = 1280, int $height = 1000)
{
    $page = visit("/products/{$product['id']}")->resize($width, $height);
    // The loader too: a test that samples what is under a point would find it.
    waitUntil($page, "document.querySelector('#thumb-strip .strip-thumb') !== null && !document.getElementById('page-loader')");

    return $page;
}

/** Not waiting on the strip: a colour with one photograph has nothing to preview. */
function galleryOpenSpread(array $product)
{
    $page = visit("/products/{$product['id']}")->resize(1280, 1000);
    waitUntil($page, "document.querySelector('.variant-option[aria-pressed=\"true\"]') !== null");

    return $page;
}

describe('a piece photographed twice in one colour', function () {
    beforeEach(function () {
        $this->piece = galleryPiece();
    });

    describe('the strip', function () {
        it('shows every photograph of the chosen colour', function () {
            galleryOpen($this->piece)->assertCount('.strip-thumb', 2)->assertNoJavaScriptErrors();
        });

        // A row underneath cost height, and height is what forced the stage to crop.
        it('runs down the left of the stage', function () {
            $page = galleryOpen($this->piece);
            $stage = galleryBox($page, '#gallery-stage');
            $strip = galleryBox($page, '#thumb-strip');

            expect($strip['x'] + $strip['width'])->toBeLessThanOrEqual($stage['x'] + 2, 'the strip is not beside it')
                ->and($strip['height'])->toBeGreaterThan($strip['width'], 'the strip is not a column');
        });

        it('leaves the stage the rest of the column', function () {
            $fills = galleryOpen($this->piece)->script(<<<'JS'
                (() => {
                    const el = document.getElementById('gallery-stage');
                    const column = el.closest('[class*="col-"]');
                    const style = getComputedStyle(column);
                    const inner = column.clientWidth
                        - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
                    const strip = document.getElementById('thumb-strip');
                    const taken = strip.hidden ? 0 : strip.getBoundingClientRect().width + 10;
                    return el.getBoundingClientRect().width >= inner - taken - 2;
                })()
                JS);

            expect($fills)->toBeTrue("something other than the photograph is taking the column's width");
        });

        it('changes the photograph when a thumbnail is clicked', function () {
            $page = galleryOpen($this->piece);
            $before = $page->attribute('#stage-image', 'src');

            $page->click('.strip-thumb >> nth=1');
            waitUntil($page, 'document.getElementById("stage-image").getAttribute("src") !== '.json_encode($before));

            $page->assertSeeIn('#stage-counter', '2 / 2');
        });

        it('marks the active thumbnail', function () {
            $page = galleryOpen($this->piece);
            $page->assertAttributeContains('.strip-thumb >> nth=0', 'class', 'is-active');

            $page->click('.strip-thumb >> nth=1');

            $page->assertAttributeContains('.strip-thumb >> nth=1', 'class', 'is-active')
                ->assertAttributeDoesntContain('.strip-thumb >> nth=0', 'class', 'is-active');
        });

        // The border is 2px in both states rather than growing when active.
        it('does not resize the marked thumbnail', function () {
            $page = galleryOpen($this->piece);
            $size = "(() => { const b = document.querySelectorAll('.strip-thumb')[1].getBoundingClientRect(); return [Math.round(b.width), Math.round(b.height)]; })()";
            $before = $page->script($size);

            $page->click('.strip-thumb >> nth=1');

            expect($page->script($size))->toBe($before);
        });
    });

    /*
     * A tap on the photograph opens it full screen, and nothing said so. The cue
     * is furniture, not a control — the whole stage is the target — so it lets
     * the click through.
     */
    describe('the stage says it opens', function () {
        it('puts the cue on the photograph', function () {
            galleryOpen($this->piece)->assertVisible('#stage-zoom')->assertSeeIn('#stage-zoom', 'Ampliar');
        });

        it('sits on the stage, opposite the counter', function () {
            $page = galleryOpen($this->piece);
            $zoom = galleryBox($page, '#stage-zoom');
            $counter = galleryBox($page, '#stage-counter');
            $stage = galleryBox($page, '#gallery-stage');

            expect($zoom['x'])->toBeLessThan($counter['x'])
                // On the photograph, not above or below it.
                ->and($zoom['y'])->toBeGreaterThan($stage['y'])
                ->and($zoom['y'] + $zoom['height'])->toBeLessThanOrEqual($stage['y'] + $stage['height'] + 1);
        });

        it('does not swallow the click', function () {
            expect(galleryOpen($this->piece)->script("getComputedStyle(document.getElementById('stage-zoom')).pointerEvents"))->toBe('none');
        });

        it('is hidden when there is nothing to enlarge', function () {
            $page = galleryOpen($this->piece);
            $page->click(galleryOption('Preto e Branco'));
            waitUntil($page, "document.querySelector('#gallery-stage .product-placeholder') !== null");

            $page->assertMissing('#stage-zoom');
        });

        // Unlike the counter and the strip, which need something to count.
        it('still shows the cue for one photograph', function () {
            $page = galleryOpen($this->piece);
            $page->click(galleryOption('Branco e Dourado'));
            waitUntil($page, "document.querySelector('#stage-zoom:not([hidden])') !== null");

            $page->assertVisible('#stage-zoom');
        });
    });

    // Showing another colour's photograph would be a lie about what the shopper picked.
    describe('a colour with no photographs of its own', function () {
        it('draws the placeholder rather than another colour\'s photograph', function () {
            $page = galleryOpen($this->piece);
            $photographed = $page->attribute('#stage-image', 'src');

            $page->click(galleryOption('Preto e Branco'));
            waitUntil($page, "document.querySelectorAll('#gallery-stage .product-placeholder').length === 1");

            $page->assertMissing('#stage-image')->assertNoJavaScriptErrors();
            expect($photographed)->not->toBeEmpty('the photographed colour had nothing to show either');
        });

        // The placeholder is inserted into the stage rather than replacing it, so the photograph has to come back.
        it('brings the photograph back for the photographed colour', function () {
            $page = galleryOpen($this->piece);
            $page->click(galleryOption('Preto e Branco'));
            waitUntil($page, "document.querySelector('#gallery-stage .product-placeholder') !== null");

            $page->click(galleryOption('Branco e Dourado'));
            waitUntil($page, "document.querySelectorAll('#gallery-stage .product-placeholder').length === 0");

            $page->assertVisible('#stage-image')->assertCount('.strip-thumb', 2);
        });
    });

    /*
     * The stage used to take its height from the panel beside it, which turned a
     * 4:5 photograph into a letterbox. It carries 4:5 now, and the columns are
     * proportioned so a fully described piece comes out level.
     */
    describe('the stage keeps its own shape', function () {
        it('never stretches the photograph', function () {
            $box = galleryBox(galleryOpen($this->piece), '#gallery-stage');

            expect(abs($box['width'] / $box['height'] - 0.8))->toBeLessThan(0.01);
        });

        // The gallery may be the taller of the two, never the shorter.
        it('comes out level for a described piece', function () {
            $ends = galleryOpen($this->piece)->script(<<<'JS'
                (() => {
                    const columns = [...document.querySelectorAll('#product-detail > [class*="col-"]')];
                    const lastVisible = (column) => [...column.children]
                        .filter((child) => child.getBoundingClientRect().height > 0)
                        .pop();
                    return columns.map((column) =>
                        Math.round(lastVisible(column).getBoundingClientRect().bottom));
                })()
                JS);

            expect($ends[0])->toBeGreaterThanOrEqual($ends[1] - 2, 'the panel outran the photograph: '.json_encode($ends));
        });

        // Under `contain` a square photograph left a band of paper down each side.
        it('shows no paper around the photograph', function () {
            $edges = galleryOpen($this->piece)->script(<<<'JS'
                (() => {
                    const box = document.getElementById('gallery-stage').getBoundingClientRect();
                    const points = [
                        [box.x + 6, box.y + box.height / 2],
                        [box.right - 6, box.y + box.height / 2],
                        [box.x + box.width / 2, box.y + 6],
                        [box.x + box.width / 2, box.bottom - 6],
                    ];
                    return points.map(([x, y]) => document.elementFromPoint(x, y)?.id);
                })()
                JS);

            expect($edges)->toBe(array_fill(0, 4, 'stage-image'));
        });

        // An <img> at height: 100% falls back to its own aspect ratio while the height is worked out.
        it('does not let the photograph decide the height', function () {
            expect(galleryOpen($this->piece)->script("getComputedStyle(document.getElementById('stage-image')).position"))->toBe('absolute');
        });
    });

    // They were ‹ and › characters, which needed 1.4rem to read as arrows.
    it('draws the arrows as icons rather than punctuation', function () {
        $page = galleryOpen($this->piece);

        foreach (['[data-prev]', '[data-next]'] as $control) {
            $page->assertCount("{$control} i.fa-solid", 1);
            expect(trim($page->script("document.querySelector('{$control}').innerText")))->toBe('', "{$control} still has a glyph");
        }
        $page->assertAttribute('[data-prev] i', 'class', 'fa-solid fa-chevron-left')
            ->assertAttribute('[data-next] i', 'class', 'fa-solid fa-chevron-right');
    });

    describe('on a phone', function () {
        // A row at every width, which is why the media query that turned the column into one could go.
        it('makes the strip a row the page does not scroll sideways for', function () {
            $state = galleryOpen($this->piece, 390, 780)->script(<<<'JS'
                (() => {
                    const strip = document.getElementById('thumb-strip');
                    return {
                        direction: getComputedStyle(strip).flexDirection,
                        overflowX: getComputedStyle(strip).overflowX,
                        pageScrolls: document.documentElement.scrollWidth > window.innerWidth,
                    };
                })()
                JS);

            expect($state)->toBe(['direction' => 'row', 'overflowX' => 'auto', 'pageScrolls' => false]);
        });

        it('still fits the photograph', function () {
            expect(galleryBox(galleryOpen($this->piece, 390, 780), '#gallery-stage')['width'])->toBeLessThanOrEqual(390);
        });
    });
});

/*
 * Four photographs, one on each of four colours, and a fifth colour nobody has
 * photographed. Each colour shows its own, so there is nothing to preview and the
 * strip stays away — the others are reached through the swatches.
 */
describe('a piece photographed once per colour', function () {
    beforeEach(function () {
        $product = makeProduct('Caixa Redonda Filigrana');
        $white = makeColor('Branco', '#FFFFFF');

        $this->names = ['Branco e Dourado', 'Preto e Branco', 'Vermelho e Branco', 'Azul e Branco'];
        foreach ($this->names as $name) {
            galleryUpload($product, makeVariant($product, makeColorSet($name, [$white['id']])), "{$name}.jpg");
        }
        makeVariant($product, makeColorSet('Verde e Dourado', [$white['id']]));

        $this->product = $product;
    });

    // [hidden] is display: none and an explicit display outranks it, so the previous photograph stayed behind the placeholder.
    it('shows the placeholder for a colour nobody has photographed', function () {
        $page = galleryOpenSpread($this->product);
        $page->click(galleryOption('Verde e Dourado'));
        waitUntil($page, "document.querySelector('#gallery-stage .product-placeholder') !== null");

        $page->assertMissing('#stage-image');
        expect(galleryBox($page, '#stage-image'))->toBeNull();
    });

    // Offering every colour's photographs turned the page into a tour of the whole piece.
    it('offers only the chosen colour\'s photograph', function () {
        galleryOpenSpread($this->product)
            ->assertMissing('#thumb-strip')
            ->assertMissing('#stage-counter')
            ->assertNoJavaScriptErrors();
    });

    it('keeps the arrows within the colour', function () {
        galleryOpenSpread($this->product)->assertDisabled('[data-prev]')->assertDisabled('[data-next]');
    });

    it('shows another colour\'s photograph by choosing that colour', function () {
        $page = galleryOpenSpread($this->product);
        $before = $page->attribute('#stage-image', 'src');

        $page->click(galleryOption($this->names[2]));
        waitUntil($page, 'document.getElementById("stage-image").getAttribute("src") !== '.json_encode($before));

        // It is this colour's own photograph, so nothing to disclaim.
        $page->assertMissing('#stage-note');
    });
});
