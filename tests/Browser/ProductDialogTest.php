<?php

/*
 * core/steps.js, core/modal.js and core/photo-picker.js, run in a real browser
 * through the products page: the create wizard, its colour chips and photo
 * slots, the edit dialog's colour panel, and a confirm raised over it. A real
 * browser because the bugs these catch are layout and cascade ones — a class
 * rule's display once outranked [hidden] and the Voltar button never hid.
 */

use Pest\Browser\Api\AwaitableWebpage as Webpage;
use Pest\Browser\Playwright\Page;

beforeEach(function () {
    signIn();
    makeProductType('Caixa');
});

/** Pest's Webpage has no mouse or position-aware click; the Playwright page it wraps does. */
function productDialogRaw(Webpage $page): Page
{
    return (fn () => $this->page)->call($page);
}

/**
 * Poll a JS expression in the page until it is truthy. Pest's assertions read
 * once and never wait, and these dialogs animate for up to 300ms.
 */
function productDialogWaitFor(Webpage $page, string $condition): Webpage
{
    $label = json_encode($condition);
    $page->script(<<<JS
        () => new Promise((resolve, reject) => {
            const visible = (selector) => !!document.querySelector(selector)?.checkVisibility({ visibilityProperty: true });
            const until = Date.now() + 5000;
            const tick = async () => {
                let ok = false;
                try { ok = await (async () => ($condition))(); } catch (e) {}
                if (ok) return resolve(true);
                if (Date.now() > until) return reject(new Error('Timed out waiting for: ' + {$label}));
                setTimeout(tick, 25);
            };
            tick();
        })
        JS);

    return $page;
}

function productDialogJs(Webpage $page, string $expression): mixed
{
    return $page->script("() => {$expression}");
}

function productDialogVisible(Webpage $page, string $selector): bool
{
    return productDialogRaw($page)->unstrict(fn (Page $raw) => $raw->locator($selector)->isVisible());
}

function productDialogCount(Webpage $page, string $selector): int
{
    return productDialogRaw($page)->unstrict(fn (Page $raw) => $raw->locator($selector)->count());
}

function productDialogVisit(): Webpage
{
    $page = visit('/dashboard/products')->resize(1280, 900);
    productDialogWaitFor($page, "visible('#new-product')");

    return $page;
}

/** Bootstrap moves focus in only when the 300ms slide ends; clicking a moving footer once advanced twice. */
function productDialogShown(Webpage $page, string $id): Webpage
{
    return productDialogWaitFor($page, "document.getElementById('{$id}').contains(document.activeElement)");
}

function productDialogOpenWizard(Webpage $page): Webpage
{
    $page->click('#new-product');

    return productDialogShown($page, 'newProductModal');
}

function productDialogFillIdentity(Webpage $page, string $name = 'Caixa Redonda'): Webpage
{
    $page->fill('#newProductModal [name="name"]', $name);

    return productDialogSelectType($page);
}

function productDialogSelectType(Webpage $page): Webpage
{
    productDialogWaitFor($page, "[...document.querySelectorAll('#newProductModal [name=\"type_id\"] option')].some(o => o.textContent.trim() === 'Caixa')");

    return $page->select('#newProductModal [name="type_id"]', 'Caixa');
}

function productDialogNextLabel(Webpage $page): string
{
    return productDialogJs($page, "document.querySelector('#newProductModal [data-step-next]').innerText.trim()");
}

function productDialogStepLabel(Webpage $page): string
{
    return productDialogJs($page, "document.querySelector('#newProductModal [data-step-label]').textContent");
}

/** Each advance is confirmed before the next click, so an overshoot fails here rather than creating the piece. */
function productDialogNext(Webpage $page, int $toStep): Webpage
{
    $page->click('#newProductModal [data-step-next]');

    return productDialogWaitFor($page, "document.querySelector('#newProductModal [data-step-label]').textContent.includes('Passo {$toStep} de 3')");
}

function productDialogToColourStep(Webpage $page): Webpage
{
    productDialogOpenWizard($page);
    productDialogFillIdentity($page);
    productDialogNext($page, 2);

    return productDialogNext($page, 3);
}

/** From the last step: write, and wait for the hand-over to the edit dialog. */
function productDialogFinish(Webpage $page): Webpage
{
    expect(productDialogNextLabel($page))->toBe('Criar peça');
    $page->click('#newProductModal [data-step-next]');

    return productDialogWaitFor($page, "visible('#editProductModal')");
}

function productDialogToTheEnd(Webpage $page): Webpage
{
    productDialogNext($page, 2);
    productDialogNext($page, 3);

    return productDialogFinish($page);
}

function productDialogChip(string $name): string
{
    return "#newProductModal .variant-choice:has-text(\"{$name}\")";
}

function productDialogPhotoFile(string $name): string
{
    $path = sys_get_temp_dir().'/ccg-dialog-'.$name;
    file_put_contents($path, photo($name)->getContent());

    return $path;
}

/** Choose a photograph in $scope's empty slot, the way the file dialog would. */
function productDialogPutPhoto(Webpage $page, string $scope, string $name): Webpage
{
    $page->attach("{$scope} >> .photo-slot:not(.is-filled) input[type=\"file\"]", productDialogPhotoFile($name));

    return $page;
}

function productDialogFilled(Webpage $page, string $scope): int
{
    return productDialogCount($page, "{$scope} >> .photo-slot.is-filled");
}

function productDialogTotal(): int
{
    return test()->getJson('/api/products/')->json('pagination.total');
}

/** Create a piece, optionally in a colour, and land on its colours panel. */
function productDialogOpenColours(bool $colours = true): Webpage
{
    $page = productDialogVisit();
    productDialogToColourStep($page);
    if ($colours) {
        $page->click('#newProductModal .variant-choice >> nth=0');
    }

    return productDialogFinish($page);
}

const PRODUCT_DIALOG_FIRST_ROW = '#newProductModal [data-photo-for] >> nth=0';

describe('the step dialog', function () {
    it('opens on the first step with no way back', function () {
        $page = productDialogVisit();
        productDialogOpenWizard($page);

        expect(productDialogStepLabel($page))->toContain('Passo 1 de 3')
            ->and($page->attribute('#newProductModal [data-step-progress]', 'aria-valuenow'))->toBe('1')
            // Real visibility, not the attribute: a class rule's display once outranked [hidden].
            ->and(productDialogVisible($page, '#newProductModal [data-step-back]'))->toBeFalse()
            ->and(productDialogNextLabel($page))->toBe('Continuar');
        $page->assertNoJavaScriptErrors();
    });

    it('keeps the first step\'s required fields', function () {
        $page = productDialogVisit();
        productDialogOpenWizard($page);

        $page->click('#newProductModal [data-step-next]');
        productDialogWaitFor($page, "document.querySelector('.swal2-container')?.innerText.includes('nome é obrigatório')");
        expect(productDialogStepLabel($page))->toContain('Passo 1 de 3');

        $page->fill('#newProductModal [name="name"]', 'Caixa Redonda');
        $page->click('#newProductModal [data-step-next]');
        productDialogWaitFor($page, "document.querySelector('.swal2-container')?.innerText.includes('tipo é obrigatório')");
        expect(productDialogStepLabel($page))->toContain('Passo 1 de 3');
    });

    it('lands the error in front of the dialog, not behind it', function () {
        // elementFromPoint is what catches it: the toast is present and styled
        // either way, the question is what a person sees at those coordinates.
        $page = productDialogVisit();
        productDialogOpenWizard($page);
        productDialogSelectType($page);
        $page->click('#newProductModal [data-step-next]');
        productDialogWaitFor($page, "visible('.swal2-popup')");

        $onTop = productDialogJs($page, <<<'JS'
            (() => {
                // The popup, not the container: the container is a pointer-events:none
                // frame whose centre is empty air.
                const toast = document.querySelector('.swal2-popup');
                const box = toast.getBoundingClientRect();
                const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
                const layer = (el) => Number(getComputedStyle(el).zIndex) || 0;
                return {
                    covered: !toast.contains(hit),
                    toastLayer: layer(document.querySelector('.swal2-container')),
                    modalLayer: layer(document.querySelector('.modal.show')),
                };
            })()
            JS);

        expect($onTop['covered'])->toBeFalse('the message is painting behind the dialog')
            ->and($onTop['toastLayer'])->toBeGreaterThan($onTop['modalLayer']);
    });

    it('swaps which group is on screen when advancing', function () {
        $page = productDialogVisit();
        productDialogOpenWizard($page);
        productDialogFillIdentity($page);
        productDialogNext($page, 2);

        expect($page->attribute('#newProductModal [data-step-progress]', 'aria-valuenow'))->toBe('2')
            ->and(productDialogVisible($page, '#newProductModal [name="name"]'))->toBeFalse()
            ->and(productDialogVisible($page, '#newProductModal [name="description"]'))->toBeTrue()
            ->and(productDialogVisible($page, '#newProductModal [data-step-back]'))->toBeTrue()
            ->and(productDialogNextLabel($page))->toBe('Continuar');
    });

    it('keeps every answer going back', function () {
        // The groups stay in the DOM precisely so this holds.
        $page = productDialogVisit();
        productDialogOpenWizard($page);
        productDialogFillIdentity($page);
        productDialogNext($page, 2);

        $page->fill('#newProductModal [name="description"]', 'Com filigrana na tampa.');
        $page->click('#newProductModal [data-step-back]');
        $page->assertValue('#newProductModal [name="name"]', 'Caixa Redonda');

        productDialogNext($page, 2);
        $page->assertValue('#newProductModal [name="description"]', 'Com filigrana na tampa.');
    });

    it('writes nothing until the last step', function () {
        // A piece is on the storefront the moment its row exists, with no draft flag.
        expect(productDialogTotal())->toBe(0);

        $page = productDialogVisit();
        productDialogOpenWizard($page);
        productDialogFillIdentity($page);
        productDialogNext($page, 2);
        productDialogNext($page, 3);
        expect(productDialogTotal())->toBe(0, 'reaching the last step must not create it');

        $page->keys(':focus', 'Escape');
        productDialogWaitFor($page, "!visible('#newProductModal')");
        expect(productDialogTotal())->toBe(0, 'abandoning the wizard must not create it');
    });

    it('writes once on the last step and hands over to the photographs', function () {
        $page = productDialogVisit();
        productDialogOpenWizard($page);
        productDialogFillIdentity($page);
        productDialogToTheEnd($page);

        $body = $this->getJson('/api/products/')->json();
        expect($body['pagination']['total'])->toBe(1)
            ->and($body['products'][0]['name'])->toBe('Caixa Redonda');

        // Landing on Detalhes would show the owner the form they just filled.
        expect(trim($page->text('#editProductModal #edit-tabs .nav-link.active')))->toBe('Cores e fotografias')
            ->and(productDialogVisible($page, '#editProductModal [data-panel="variants"]'))->toBeTrue()
            ->and(productDialogVisible($page, '#editProductModal [data-panel="details"]'))->toBeFalse();
        $page->assertNoJavaScriptErrors();
    });

    it('shows both groups at once when editing', function () {
        $page = productDialogVisit();
        productDialogOpenWizard($page);
        productDialogFillIdentity($page);
        productDialogToTheEnd($page);

        $page->click('#editProductModal #edit-tabs [data-tab="details"] .nav-link');

        expect(productDialogVisible($page, '#editProductModal [name="name"]'))->toBeTrue()
            ->and(productDialogVisible($page, '#editProductModal [name="description"]'))->toBeTrue()
            ->and(productDialogCount($page, '#editProductModal [data-step-label]'))->toBe(0);
    });
});

describe('choosing colours while creating', function () {
    // A variant needs a product id, so the choice is held in the page and posted
    // once the product exists — without weakening "nothing is written until the end".
    beforeEach(function () {
        $white = makeColor('Branco', '#FFFFFF');
        $gold = makeColor('Dourado', '#C8A24B');
        $black = makeColor('Preto', '#111111');
        makeColorSet('Branco e Dourado', [$white['id'], $gold['id']]);
        makeColorSet('Preto e Dourado', [$black['id'], $gold['id']]);
    });

    it('offers every colour set on the third step', function () {
        $page = productDialogVisit();
        productDialogToColourStep($page);

        expect(productDialogCount($page, '#newProductModal .variant-choice'))->toBe(2)
            ->and(productDialogNextLabel($page))->toBe('Criar peça');
        $page->assertNoJavaScriptErrors();
    });

    it('allows choosing none', function () {
        $page = productDialogVisit();
        productDialogToColourStep($page);
        productDialogFinish($page);

        expect($this->getJson('/api/products/')->json('products.0.variants'))->toBe([]);
    });

    it('attaches the chosen colours to the new piece', function () {
        $page = productDialogVisit();
        productDialogToColourStep($page);
        $page->click(productDialogChip('Branco e Dourado'));
        $page->click(productDialogChip('Preto e Dourado'));
        productDialogFinish($page);

        $names = collect($this->getJson('/api/products/')->json('products.0.variants'))
            ->pluck('color_set.name')->sort()->values()->all();
        expect($names)->toBe(['Branco e Dourado', 'Preto e Dourado']);
        $page->assertNoJavaScriptErrors();
    });

    it('lets a chip be unchosen', function () {
        $page = productDialogVisit();
        productDialogToColourStep($page);

        $page->click(productDialogChip('Branco e Dourado'));
        $page->assertAttribute(productDialogChip('Branco e Dourado'), 'aria-pressed', 'true');
        $page->click(productDialogChip('Branco e Dourado'));
        $page->assertAttribute(productDialogChip('Branco e Dourado'), 'aria-pressed', 'false');

        productDialogFinish($page);
        expect($this->getJson('/api/products/')->json('products.0.variants'))->toBe([]);
    });

    it('writes nothing for a chosen colour before the last button', function () {
        $page = productDialogVisit();
        productDialogToColourStep($page);
        $page->click('#newProductModal .variant-choice >> nth=0');
        expect(productDialogTotal())->toBe(0, 'picking a colour created the piece');

        $page->keys(':focus', 'Escape');
        productDialogWaitFor($page, "!visible('#newProductModal')");
        expect(productDialogTotal())->toBe(0);
    });

    it('shows a photo slot only for the colours chosen', function () {
        // Nine colour sets must not mean nine file pickers.
        $page = productDialogVisit();
        productDialogToColourStep($page);
        expect(productDialogVisible($page, '#newProductModal #variant-photos'))->toBeFalse();

        $page->click(productDialogChip('Branco e Dourado'));
        expect(productDialogVisible($page, '#newProductModal #variant-photos'))->toBeTrue()
            ->and(productDialogCount($page, '#newProductModal [data-photo-for]'))->toBe(1);

        $page->click(productDialogChip('Preto e Dourado'));
        expect(productDialogCount($page, '#newProductModal [data-photo-for]'))->toBe(2);

        $page->click(productDialogChip('Preto e Dourado'));
        expect(productDialogCount($page, '#newProductModal [data-photo-for]'))->toBe(1);
        $page->assertNoJavaScriptErrors();
    });

    it('keeps a photo chosen for one colour when another is ticked', function () {
        // A tray redrawn from scratch would lose its files, so rows are moved, not rebuilt.
        $page = productDialogVisit();
        productDialogToColourStep($page);

        $page->click(productDialogChip('Branco e Dourado'));
        productDialogPutPhoto($page, PRODUCT_DIALOG_FIRST_ROW, 'caixa.jpg');
        productDialogWaitFor($page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 1");

        $page->click(productDialogChip('Preto e Dourado'));
        expect(productDialogCount($page, '#newProductModal [data-photo-for]'))->toBe(2)
            ->and(productDialogFilled($page, '#newProductModal'))->toBe(1, 'the held photograph was lost')
            ->and(productDialogFilled($page, PRODUCT_DIALOG_FIRST_ROW))->toBe(1);
    });

    it('lets a colour hold several photographs', function () {
        $page = productDialogVisit();
        productDialogToColourStep($page);
        $page->click(productDialogChip('Branco e Dourado'));

        productDialogPutPhoto($page, PRODUCT_DIALOG_FIRST_ROW, 'uma.jpg');
        productDialogWaitFor($page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 1");
        productDialogPutPhoto($page, PRODUCT_DIALOG_FIRST_ROW, 'outra.jpg');
        productDialogWaitFor($page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 2");

        expect(productDialogFilled($page, PRODUCT_DIALOG_FIRST_ROW))->toBe(2)
            ->and(productDialogCount($page, PRODUCT_DIALOG_FIRST_ROW.' >> .photo-slot:not(.is-filled)'))->toBe(1);
    });

    it('lets the photo be taken back', function () {
        // The whole area removes it, not just the ×.
        $page = productDialogVisit();
        productDialogToColourStep($page);
        $page->click(productDialogChip('Branco e Dourado'));
        productDialogPutPhoto($page, PRODUCT_DIALOG_FIRST_ROW, 'caixa.jpg');
        productDialogWaitFor($page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 1");

        $page->click(PRODUCT_DIALOG_FIRST_ROW.' >> .photo-slot.is-filled');

        expect(productDialogFilled($page, PRODUCT_DIALOG_FIRST_ROW))->toBe(0)
            ->and(productDialogCount($page, PRODUCT_DIALOG_FIRST_ROW.' >> .photo-slot'))->toBe(1);
    });

    it('lands the photo on its own variant', function () {
        $page = productDialogVisit();
        productDialogToColourStep($page);
        $page->click(productDialogChip('Branco e Dourado'));
        $page->click(productDialogChip('Preto e Dourado'));
        // The second row's tray: the first colour deliberately gets none.
        productDialogPutPhoto($page, '#newProductModal [data-photo-for] >> nth=1', 'preto.jpg');
        productDialogWaitFor($page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 1");

        // The in-process server parses multipart bodies with mb_ltrim(), which
        // turns a JPEG's non-UTF-8 bytes into "?" under the default encoding.
        $encoding = mb_internal_encoding();
        mb_internal_encoding('8bit');
        try {
            productDialogFinish($page);
        } finally {
            mb_internal_encoding($encoding);
        }

        $bySet = collect($this->getJson('/api/products/')->json('products.0.variants'))->keyBy('color_set.name');
        expect($bySet['Branco e Dourado']['images'])->toBe([])
            ->and($bySet['Preto e Dourado']['images'])->toHaveCount(1)
            ->and($bySet['Preto e Dourado']['images'][0]['url'])->toEndWith('.jpg');
        $page->assertNoJavaScriptErrors();
    });

    it('drops the photo too when its colour is unticked', function () {
        // Otherwise the upload arrives for a variant the piece does not have.
        $page = productDialogVisit();
        productDialogToColourStep($page);
        $page->click(productDialogChip('Branco e Dourado'));
        productDialogPutPhoto($page, PRODUCT_DIALOG_FIRST_ROW, 'caixa.jpg');
        productDialogWaitFor($page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 1");
        $page->click(productDialogChip('Branco e Dourado'));
        $page->click(productDialogChip('Preto e Dourado'));
        productDialogFinish($page);

        $variants = $this->getJson('/api/products/')->json('products.0.variants');
        expect(array_column(array_column($variants, 'color_set'), 'name'))->toBe(['Preto e Dourado'])
            ->and($variants[0]['images'])->toBe([]);
    });

    it('writes nothing for a photo before the last button', function () {
        $page = productDialogVisit();
        productDialogToColourStep($page);
        $page->click(productDialogChip('Branco e Dourado'));
        productDialogPutPhoto($page, PRODUCT_DIALOG_FIRST_ROW, 'caixa.jpg');
        productDialogWaitFor($page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 1");

        expect(productDialogTotal())->toBe(0, 'choosing a photograph created the piece');
    });

    it('does not hide the selected ring behind the badge', function () {
        // The badge brings its own background; an inset shadow would paint beneath it.
        $page = productDialogVisit();
        productDialogToColourStep($page);

        $measure = "(() => { const el = document.querySelector('#newProductModal .variant-choice'); const s = getComputedStyle(el); const b = el.getBoundingClientRect(); return { w: Math.round(b.width), h: Math.round(b.height), shadow: s.boxShadow, border: s.borderTopWidth }; })()";
        $before = productDialogJs($page, $measure);
        $page->click('#newProductModal .variant-choice >> nth=0');
        $after = productDialogJs($page, $measure);

        expect($after['shadow'])->toBe('none')
            ->and($after['border'])->toBe('2px')
            ->and([$after['w'], $after['h']])->toBe([$before['w'], $before['h']], 'choosing a colour resized the chip');
    });
});

describe('the photo picker', function () {
    // Driven through the wizard's colour step, one of its real callers.
    beforeEach(function () {
        makeColorSet('Branco e Dourado', [makeColor('Branco', '#FFFFFF')['id']]);

        $this->page = productDialogVisit();
        productDialogToColourStep($this->page);
        $this->page->click('#newProductModal .variant-choice >> nth=0');
    });

    it('invites all three ways in when empty', function () {
        // One input covers choose and shoot (accept, capture); the slot takes drops.
        $row = PRODUCT_DIALOG_FIRST_ROW;
        expect(productDialogCount($this->page, "{$row} >> .photo-slot .photo-slot-icon .fa-camera"))->toBe(1)
            ->and($this->page->attribute("{$row} >> .photo-slot input[type=\"file\"]", 'capture'))->toBe('environment')
            ->and($this->page->attribute("{$row} >> .photo-slot input[type=\"file\"]", 'accept'))->toContain('image/jpeg');
        $this->page->assertNoJavaScriptErrors();
    });

    it('hides the input but keeps it reachable by keyboard', function () {
        // display: none would take it out of the tab order.
        $state = productDialogJs($this->page, "(() => { const s = getComputedStyle(document.querySelector('#newProductModal [data-photo-for] .photo-slot input[type=\"file\"]')); return { display: s.display, opacity: s.opacity }; })()");

        expect($state['display'])->not->toBe('none')
            ->and($state['opacity'])->toBe('0');
    });

    it('fills the area with a chosen photograph', function () {
        productDialogPutPhoto($this->page, PRODUCT_DIALOG_FIRST_ROW, 'caixa.jpg');
        productDialogWaitFor($this->page, "document.querySelector('#newProductModal .photo-slot.is-filled img')?.complete");

        // Against the slot's inner box: the image sits inside the 2px border.
        $result = productDialogJs($this->page, <<<'JS'
            (() => {
                const el = document.querySelector('#newProductModal .photo-slot.is-filled');
                const img = el.querySelector('img');
                const box = img.getBoundingClientRect();
                return {
                    fills: Math.abs(box.width - el.clientWidth) < 1 && Math.abs(box.height - el.clientHeight) < 1,
                    fit: getComputedStyle(img).objectFit,
                    src: img.getAttribute('src'),
                };
            })()
            JS);

        expect($result['fills'])->toBeTrue('the photograph does not fill its slot')
            ->and($result['fit'])->toBe('cover')
            ->and($result['src'])->toStartWith('blob:');
    });

    it('turns the border solid once it holds something', function () {
        $style = "getComputedStyle(document.querySelector('#newProductModal [data-photo-for] .photo-slot')).borderTopStyle";
        expect(productDialogJs($this->page, $style))->toBe('dashed');

        productDialogPutPhoto($this->page, PRODUCT_DIALOG_FIRST_ROW, 'caixa.jpg');
        productDialogWaitFor($this->page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 1");
        expect(productDialogJs($this->page, "getComputedStyle(document.querySelector('#newProductModal .photo-slot.is-filled')).borderTopStyle"))->toBe('solid');
    });

    it('shows the cross on hover and removes from anywhere in the area', function () {
        productDialogPutPhoto($this->page, PRODUCT_DIALOG_FIRST_ROW, 'caixa.jpg');
        productDialogWaitFor($this->page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 1");

        expect(productDialogJs($this->page, "getComputedStyle(document.querySelector('.photo-slot.is-filled .photo-slot-x')).opacity"))->toBe('0');

        $this->page->hover('#newProductModal .photo-slot.is-filled');
        productDialogWaitFor($this->page, "getComputedStyle(document.querySelector('.photo-slot.is-filled .photo-slot-x')).opacity === '1'");

        // Not the × itself: anywhere in the area takes the photograph back.
        productDialogRaw($this->page)->locator('#newProductModal .photo-slot.is-filled')
            ->click(['position' => ['x' => 8, 'y' => 40]]);
        expect(productDialogFilled($this->page, PRODUCT_DIALOG_FIRST_ROW))->toBe(0);
    });

    it('replaces what is there when dropped over a filled slot', function () {
        // The one way to swap a photograph, since clicking removes it.
        productDialogPutPhoto($this->page, PRODUCT_DIALOG_FIRST_ROW, 'primeira.jpg');
        productDialogWaitFor($this->page, "document.querySelectorAll('#newProductModal .photo-slot.is-filled').length === 1");
        $first = $this->page->attribute('#newProductModal .photo-slot.is-filled img', 'src');

        $this->page->script(<<<'JS'
            () => new Promise((resolve) => {
                const element = document.querySelector('#newProductModal .photo-slot.is-filled');
                const canvas = document.createElement('canvas');
                canvas.width = canvas.height = 8;
                canvas.toBlob((blob) => {
                    const transfer = new DataTransfer();
                    transfer.items.add(new File([blob], 'segunda.jpg', { type: 'image/png' }));
                    const event = new DragEvent('drop', { bubbles: true, cancelable: true });
                    Object.defineProperty(event, 'dataTransfer', { value: transfer });
                    element.dispatchEvent(event);
                    resolve();
                }, 'image/png');
            })
            JS);
        productDialogWaitFor($this->page, "document.querySelector('#newProductModal .photo-slot.is-filled img')?.getAttribute('src') !== ".json_encode($first));

        expect(productDialogFilled($this->page, PRODUCT_DIALOG_FIRST_ROW))->toBe(1, 'the drop added a slot instead of replacing');
    });

    it('says so when dragged over', function () {
        $this->page->script(<<<'JS'
            () => {
                const slot = document.querySelector('.photo-slot');
                const event = new DragEvent('dragover', { bubbles: true, cancelable: true });
                Object.defineProperty(event, 'dataTransfer', { value: new DataTransfer() });
                slot.dispatchEvent(event);
            }
            JS);

        $this->page->assertAttributeContains(PRODUCT_DIALOG_FIRST_ROW.' >> .photo-slot', 'class', 'is-over');
    });

    it('refuses a file that is not an image before any upload', function () {
        $notes = sys_get_temp_dir().'/notas.txt';
        file_put_contents($notes, 'nada');

        $this->page->attach(PRODUCT_DIALOG_FIRST_ROW.' >> .photo-slot input[type="file"]', $notes);
        productDialogWaitFor($this->page, "document.querySelector('.swal2-container')?.innerText.includes('não é uma imagem')");

        expect(productDialogFilled($this->page, PRODUCT_DIALOG_FIRST_ROW))->toBe(0);
    });

    it('refuses a file over five megabytes', function () {
        $heavy = sys_get_temp_dir().'/grande.jpg';
        file_put_contents($heavy, "\xff\xd8\xff\xe0".str_repeat('0', 5 * 1024 * 1024));

        $this->page->attach(PRODUCT_DIALOG_FIRST_ROW.' >> .photo-slot input[type="file"]', $heavy);
        productDialogWaitFor($this->page, "document.querySelector('.swal2-container')?.innerText.includes('MB')");

        expect(productDialogFilled($this->page, PRODUCT_DIALOG_FIRST_ROW))->toBe(0);
    });
});

describe('colours and photographs are one panel', function () {
    // A photograph belongs to a colour, so a separate photographs tab was the same fact twice.
    beforeEach(function () {
        makeColorSet('Branco e Dourado', [makeColor('Branco', '#FFFFFF')['id']]);
    });

    it('has no photographs tab', function () {
        $page = productDialogOpenColours();

        $tabs = array_map('trim', productDialogJs($page, "[...document.querySelectorAll('#editProductModal #edit-tabs li')].map(li => li.textContent)"));
        expect($tabs)->toBe(['Detalhes', 'Cores e fotografias'])
            ->and(productDialogCount($page, '#editProductModal [data-panel="images"]'))->toBe(0);
        $page->assertNoJavaScriptErrors();
    });

    it('gives each colour its own photographs', function () {
        // One tray per colour, in the row that names it.
        $page = productDialogOpenColours();

        expect(productDialogCount($page, '#editProductModal [data-variant-block]'))->toBe(1)
            ->and(productDialogCount($page, '#editProductModal [data-variant-block] .photo-slot'))->toBeGreaterThanOrEqual(1)
            ->and(productDialogCount($page, '#editProductModal [data-variant-block] [data-remove-variant]'))->toBe(1);
    });

    it('says what to do for a piece with no colours', function () {
        $page = productDialogOpenColours(colours: false);
        $panel = '#editProductModal [data-panel="variants"]';

        expect(productDialogCount($page, "{$panel} [data-variant-block]"))->toBe(0)
            ->and(productDialogCount($page, "{$panel} .photo-slot"))->toBe(0, 'nowhere to put a photograph until there is a colour')
            ->and(productDialogJs($page, "document.querySelector('{$panel}').innerText"))->toContain('Sem cores associadas');
    });

    // Adding a colour re-renders the dialog while it is up. Saving afterwards used
    // to wait for a "shown" event that never came, and the spinner never stopped.
    it('still closes on save after a colour was added in it', function () {
        $page = productDialogOpenColours(colours: false);
        // Fully up, as it is by the time a person reaches for the button. While
        // it is still sliding in, the shown event is yet to come and hides the bug.
        productDialogWaitFor($page, "document.getElementById('editProductModal').classList.contains('show') && !document.querySelector('.modal.fade:not(.show)[style*=\"display: block\"]')");
        $page->wait(0.5);

        $page->click('#editProductModal #add-variant');
        productDialogWaitFor($page, "document.querySelectorAll('#editProductModal [data-variant-block]').length === 1");

        $page->click('#editProductModal #edit-tabs [data-bs-target="#edit-pane-details"]');
        $page->click('#editProductModal #edit-submit');
        productDialogWaitFor($page, "!document.getElementById('editProductModal').classList.contains('show')");

        $page->assertNoJavaScriptErrors();
    });

    // Every save remounted the filter bar, appending each type and collection
    // again, until the Tipo menu listed every family several times over.
    it('keeps one filter option per type after saving', function () {
        $page = productDialogOpenColours(colours: false);
        productDialogWaitFor($page, "document.getElementById('editProductModal').classList.contains('show')");

        $page->click('#editProductModal #edit-tabs [data-bs-target="#edit-pane-details"]');
        $page->click('#editProductModal #edit-submit');
        productDialogWaitFor($page, "!document.getElementById('editProductModal').classList.contains('show')");

        $values = productDialogJs($page, "[...document.querySelectorAll('#filter-type option')].map(o => o.value)");
        expect($values)->toBe(array_values(array_unique($values)));
    });

    it('refuses to upload a photograph with no colour', function () {
        // Belt as well as braces: the function behind the panel will not do it either.
        $page = productDialogOpenColours();

        $refusal = $page->script(<<<'JS'
            async () => {
                const module = await import('/static/js/dashboard/products/images.js');
                try {
                    await module.uploadImage(1, { file: new File(['x'], 'a.jpg') });
                    return null;
                } catch (error) {
                    return error.message;
                }
            }
            JS);

        expect($refusal)->not->toBeNull()->toContain('cor');
    });
});

describe('a confirm raised from inside a dialog', function () {
    // The question renders inside the edit dialog so it is not behind the
    // backdrop, which nests two overlays that both listen for Escape. The caller
    // must never be left awaiting a promise that does not settle.
    beforeEach(function () {
        makeProduct('Caixa Redonda');

        $this->page = productDialogVisit();
        productDialogWaitFor($this->page, "visible('#product-list tr[data-product-id]')");
        $this->page->click('#product-list tr[data-product-id] >> nth=0');
        productDialogWaitFor($this->page, "visible('#editProductModal')");
        $this->page->script(<<<'JS'
            async () => {
                const { Notify } = await import('/static/js/core/notify.js');
                window.__answer = 'pending';
                Notify.confirm('Remover esta cor?', { danger: true })
                    .then(value => { window.__answer = value; });
            }
            JS);
        productDialogWaitFor($this->page, "visible('.swal2-popup')");
    });

    it('paints over the dialog it was raised from', function () {
        $state = productDialogJs($this->page, <<<'JS'
            (() => {
                const popup = document.querySelector('.swal2-popup');
                const box = popup.getBoundingClientRect();
                const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
                const button = [...popup.querySelectorAll('button')]
                    .find(b => b.textContent.trim() === 'Confirmar' || b.textContent.trim() === 'Cancelar');
                const rect = button.getBoundingClientRect();
                const overButton = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2);
                return {
                    covered: !popup.contains(hit),
                    buttonReachable: button.contains(overButton) || button === overButton,
                };
            })()
            JS);

        expect($state['covered'])->toBeFalse()
            ->and($state['buttonReachable'])->toBeTrue('a question nobody can answer is worse than none');
    });

    it('settles the promise on Escape instead of stranding it', function () {
        $this->page->keys(':focus', 'Escape');
        productDialogWaitFor($this->page, "window.__answer !== 'pending'");

        expect(productDialogJs($this->page, 'window.__answer'))->toBeFalse('Escape means no');
    });

    it('settles the promise on cancel and leaves the dialog open', function () {
        $this->page->click('.swal2-cancel');
        productDialogWaitFor($this->page, "window.__answer !== 'pending'");

        expect(productDialogJs($this->page, 'window.__answer'))->toBeFalse()
            ->and(productDialogVisible($this->page, '#editProductModal'))->toBeTrue('answering the question must not close the form');
    });
});
