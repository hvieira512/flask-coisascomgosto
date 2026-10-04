<?php

/*
 * The collection dialog in a real browser: the fields beside the cover (stacked
 * on a phone), and the colour sets the collection gathers. A set may be in
 * several collections at once, so choosing one here must not take it from
 * another — the form used to move it.
 */

use Pest\Browser\Api\AwaitableWebpage as Webpage;

beforeEach(function () {
    signIn();
});

/** Poll a JS expression in the page until it is truthy (it may await). */
function collectionDialogWaitFor(Webpage $page, string $condition): Webpage
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

function collectionDialogBox(Webpage $page, string $selector): array
{
    return $page->script("() => { const b = document.querySelector('{$selector}').getBoundingClientRect(); return { x: b.x, y: b.y, width: b.width, height: b.height }; }");
}

function collectionDialogOpenNew(int $width = 1280, int $height = 900): Webpage
{
    $page = visit('/dashboard/collections')->resize($width, $height);
    collectionDialogWaitFor($page, "visible('#new-collection')");
    $page->click('#new-collection');

    return collectionDialogWaitFor($page, "visible('#newCollectionModal') && visible('#newCollectionModal #cof-cover .photo-slot')");
}

function collectionDialogChip(string $name): string
{
    return "#editCollectionModal .variant-choice:has-text(\"{$name}\") >> nth=0";
}

function collectionDialogNames(Webpage $page): array
{
    return $page->script("() => [...document.querySelectorAll('#editCollectionModal #cof-sets .variant-choice')].map(c => c.textContent.trim())");
}

/** Save, then wait until the set's collections satisfy $check, a JS predicate over their names. */
function collectionDialogSaveAndExpect(Webpage $page, string $set, string $check): void
{
    $page->click('#editCollectionModal [data-dialog-submit]');
    collectionDialogWaitFor($page, "!visible('#editCollectionModal')");
    collectionDialogWaitFor($page, <<<JS
        (async () => {
            const body = await fetch('/api/color-sets/?limit=100').then(r => r.json());
            const names = body.color_sets.find(s => s.name === '{$set}').collections.map(c => c.name);
            return ({$check})(names);
        })()
        JS);
}

describe('the collection form is split', function () {
    it('sits the cover beside the fields', function () {
        $page = collectionDialogOpenNew();
        // The dialog scales in; measure the settled box.
        collectionDialogWaitFor($page, "document.getElementById('newCollectionModal').getAnimations({ subtree: true }).length === 0");

        $name = collectionDialogBox($page, '#newCollectionModal #cof-name');
        $cover = collectionDialogBox($page, '#newCollectionModal #cof-cover .photo-slot');

        expect($cover['x'])->toBeGreaterThan($name['x'] + $name['width'], 'the cover is not to the right')
            ->and(abs($cover['y'] - $name['y']))->toBeLessThan(40, 'they are not on the same row');
        $page->assertNoJavaScriptErrors();
    });

    it('stacks on a phone', function () {
        // col-md stacks below 768px.
        $page = collectionDialogOpenNew(390, 780);
        collectionDialogWaitFor($page, "document.getElementById('newCollectionModal').getAnimations({ subtree: true }).length === 0");

        $name = collectionDialogBox($page, '#newCollectionModal #cof-name');
        $cover = collectionDialogBox($page, '#newCollectionModal #cof-cover .photo-slot');
        expect($cover['y'])->toBeGreaterThan($name['y'] + $name['height'], 'still side by side at 390px');

        // Tried rather than measured: scrollWidth counts the fixed offcanvas and
        // the table's own scrollport, and reads 918 on a page that cannot move.
        $moved = $page->script('() => { window.scrollTo(200, 0); const x = window.scrollX; window.scrollTo(0, 0); return x; }');
        expect($moved)->toBe(0, 'the page scrolls sideways with the dialog open');
    });

    it('does not have to be scrolled to reach the cover', function () {
        $page = collectionDialogOpenNew();

        expect($page->script("() => { const el = document.querySelector('#newCollectionModal .modal-body'); return el.scrollHeight > el.clientHeight + 1; }"))->toBeFalse();
    });
});

describe('choosing a collection\'s colour sets', function () {
    beforeEach(function () {
        $white = makeColor('Branco', '#FFFFFF');
        $blue = makeColor('Azul', '#2C5FA8');
        $filigrana = makeCollection('Filigrana');
        $bordados = makeCollection('Bordados');

        $mine = makeColorSet('Branco e Dourado', [$white['id']]);
        $theirs = makeColorSet('Branco e Azul', [$blue['id']]);
        makeColorSet('Preto e Branco', [$white['id']]);
        $this->putJson("/api/collections/{$filigrana['id']}/color-sets", ['color_set_ids' => [$mine['id']]])->assertOk();
        $this->putJson("/api/collections/{$bordados['id']}/color-sets", ['color_set_ids' => [$theirs['id']]])->assertOk();

        $this->page = visit('/dashboard/collections')->resize(1280, 900);
        collectionDialogWaitFor($this->page, "visible('#collection-rows tr')");
        $this->page->click('#collection-rows tr:has-text("Filigrana") >> nth=0');
        collectionDialogWaitFor($this->page, "visible('#editCollectionModal') && document.querySelector('#editCollectionModal #cof-sets .variant-choice')");
    });

    it('offers every colour set', function () {
        $names = collectionDialogNames($this->page);
        sort($names);

        expect($names)->toBe(['Branco e Azul', 'Branco e Dourado', 'Preto e Branco']);
        $this->page->assertNoJavaScriptErrors();
    });

    it('has the ones it gathers already chosen', function () {
        $this->page->assertAttribute(collectionDialogChip('Branco e Dourado'), 'aria-pressed', 'true')
            ->assertAttribute(collectionDialogChip('Preto e Branco'), 'aria-pressed', 'false');
    });

    it('says where else one another collection has is', function () {
        // Information rather than a warning: choosing it here does not take it from Bordados.
        $this->page->assertAttribute(collectionDialogChip('Branco e Azul'), 'title', 'Branco e Azul — também em Bordados');
    });

    it('lists the ones it gathers first', function () {
        expect(collectionDialogNames($this->page)[0])->toBe('Branco e Dourado');
    });

    it('assigns a chosen one on save', function () {
        $this->page->click(collectionDialogChip('Preto e Branco'));
        collectionDialogSaveAndExpect($this->page, 'Preto e Branco', "names => names.includes('Filigrana')");
    });

    it('drops an unchosen one from this collection only', function () {
        $this->page->click(collectionDialogChip('Branco e Dourado'));
        collectionDialogSaveAndExpect($this->page, 'Branco e Dourado', "names => !names.includes('Filigrana')");
    });

    it('leaves one another collection has there too', function () {
        $this->page->click(collectionDialogChip('Branco e Azul'));
        collectionDialogSaveAndExpect($this->page, 'Branco e Azul', "names => names.sort().join(',') === 'Bordados,Filigrana'");
    });

    it('does not let the ring be mistaken for the badge\'s own border', function () {
        // A blue set's 1px badge border looked like the ring pressed against it, so
        // the chip keeps a gap; and a ring as inset shadow would be painted over.
        $style = $this->page->script("() => { const s = getComputedStyle(document.querySelector('#editCollectionModal .variant-choice')); return { padding: parseFloat(s.paddingTop), shadow: s.boxShadow, width: s.borderTopWidth }; }");

        expect($style['shadow'])->toBe('none')
            ->and($style['width'])->toBe('2px')
            ->and($style['padding'])->toBeGreaterThanOrEqual(2);
    });

    it('does not move the chip when choosing', function () {
        // The dialog scales in over .18s; a box measured too early is a transformed one.
        collectionDialogWaitFor($this->page, "document.getElementById('editCollectionModal').getAnimations().length === 0");

        $measure = "() => { const c = [...document.querySelectorAll('#editCollectionModal .variant-choice')].find(c => c.textContent.includes('Preto e Branco')); const b = c.getBoundingClientRect(); return [Math.round(b.width), Math.round(b.height)]; }";
        $before = $this->page->script($measure);
        $this->page->click(collectionDialogChip('Preto e Branco'));

        expect($this->page->script($measure))->toBe($before);
    });
});
