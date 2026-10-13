<?php

/*
 * core/modal.js through the product types page: what showModal() buys, and
 * what formDialog and confirmDialog wire.
 */

use Pest\Browser\Api\AwaitableWebpage as Webpage;
use Pest\Browser\Playwright\Page;

beforeEach(function () {
    signIn();
});

/** Pest's Webpage has no position-aware click; the Playwright page it wraps does. */
function typeDialogRaw(Webpage $page): Page
{
    return (fn () => $this->page)->call($page);
}

/** Poll a JS expression in the page until it is truthy. */
function typeDialogWaitFor(Webpage $page, string $condition): Webpage
{
    $label = json_encode($condition);
    $budget = BROWSER_WAIT_SECONDS * 1000;
    $page->script(<<<JS
        () => new Promise((resolve, reject) => {
            const visible = (selector) => !!document.querySelector(selector)?.checkVisibility({ visibilityProperty: true });
            const until = Date.now() + {$budget};
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

function typeDialogVisit(): Webpage
{
    $page = visit('/dashboard/types')->resize(1280, 900);

    return typeDialogWaitFor($page, "visible('#new-type')");
}

/**
 * Bootstrap moves focus in only once the fade ends, and listens for Escape on
 * the modal itself; hide() during the show transition is dropped.
 */
function typeDialogShown(Webpage $page, string $id): Webpage
{
    return typeDialogWaitFor($page, "document.getElementById('{$id}').contains(document.activeElement)");
}

function typeDialogOpenNew(Webpage $page): Webpage
{
    $page->click('#new-type');

    return typeDialogWaitFor($page, "visible('#newTypeModal')");
}

function typeDialogCreate(Webpage $page, string $name): Webpage
{
    typeDialogOpenNew($page);
    $page->fill('#newTypeModal #tf-name', $name);
    $page->click('#newTypeModal [data-dialog-submit]');
    typeDialogWaitFor($page, "!visible('#newTypeModal')");

    return typeDialogWaitFor($page, "[...document.querySelectorAll('#type-rows tr')].some(r => r.textContent.includes('{$name}'))");
}

function typeDialogIsShown(Webpage $page, string $id): bool
{
    return $page->script("() => document.getElementById('{$id}').classList.contains('show')");
}

it('starts in the first field, not on the close button', function () {
    // Bootstrap focuses the modal box itself, leaving Enter wired to "close".
    $page = typeDialogVisit();
    typeDialogOpenNew($page);
    typeDialogShown($page, 'newTypeModal');

    typeDialogWaitFor($page, "document.activeElement.id === 'tf-name'");
    expect($page->script('() => document.activeElement.id'))->toBe('tf-name');
});

it('closes on Escape and the markup stays', function () {
    // The modal staying in the DOM is why every form inside one is looked up through its own modal.
    $page = typeDialogVisit();
    typeDialogOpenNew($page);
    typeDialogShown($page, 'newTypeModal');

    $page->keys(':focus', 'Escape');
    typeDialogWaitFor($page, "!visible('#newTypeModal')");

    $page->assertCount('#newTypeModal', 1);
    expect(typeDialogIsShown($page, 'newTypeModal'))->toBeFalse();
});

it('still closes on a click on the backdrop', function () {
    // Bootstrap reads the dismissal off the .modal element, the box the card floats in.
    $page = typeDialogVisit();
    typeDialogOpenNew($page);
    typeDialogShown($page, 'newTypeModal');

    typeDialogRaw($page)->locator('#newTypeModal')->click(['position' => ['x' => 8, 'y' => 8]]);
    typeDialogWaitFor($page, "!visible('#newTypeModal')");

    expect(typeDialogIsShown($page, 'newTypeModal'))->toBeFalse();
});

it('does not close on a click inside the card', function () {
    $page = typeDialogVisit();
    typeDialogOpenNew($page);

    typeDialogRaw($page)->locator('#newTypeModal .modal-body')->click(['position' => ['x' => 4, 'y' => 4]]);
    usleep(200_000);

    $page->assertVisible('#newTypeModal');
});

it('keeps the create and edit dialogs from reading each other\'s fields', function () {
    // Both hold a #tf-name and the closed one stays in the DOM, so a lookup by id
    // alone found the create form and posted a new type instead of updating one.
    $page = typeDialogVisit();
    typeDialogCreate($page, 'Moldura');

    $page->click('#type-rows tr:has-text("Moldura") >> nth=0');
    typeDialogWaitFor($page, "visible('#editTypeModal')");
    $page->assertValue('#editTypeModal #tf-name', 'Moldura');

    $page->fill('#editTypeModal #tf-name', 'Moldura grande');
    $page->click('#editTypeModal [data-dialog-submit]');
    typeDialogWaitFor($page, "!visible('#editTypeModal')");

    $names = array_column($this->getJson('/api/product-types/')->json('product_types'), 'name');
    expect($names)->toBe(['Moldura grande'], 'an update must not create a second row');
});

it('says so on a failed submit and keeps the dialog open', function () {
    // Losing what was typed because the name is taken is the worst possible answer.
    makeProductType('Caixa');
    $page = typeDialogVisit();
    typeDialogOpenNew($page);

    $page->fill('#newTypeModal #tf-name', 'Caixa');
    $page->click('#newTypeModal [data-dialog-submit]');
    typeDialogWaitFor($page, "visible('.swal2-container')");

    $page->assertVisible('#newTypeModal')
        ->assertValue('#newTypeModal #tf-name', 'Caixa');
    expect($page->script("() => document.querySelector('#newTypeModal [data-dialog-submit]').classList.contains('is-loading')"))
        ->toBeFalse('the spinner has to come off, or the button is dead for good');
});

it('runs the action on confirm and not on cancel', function () {
    $page = typeDialogVisit();
    typeDialogCreate($page, 'Bastidor');
    $delete = '#type-rows tr:has-text("Bastidor") >> nth=0 >> [data-type-action="delete"]';

    $page->click($delete);
    typeDialogWaitFor($page, "visible('#deleteTypeModal')");
    typeDialogShown($page, 'deleteTypeModal');
    $page->click('#deleteTypeModal [data-bs-dismiss="modal"] >> nth=-1');
    typeDialogWaitFor($page, "!visible('#deleteTypeModal')");
    expect($this->getJson('/api/product-types/')->json('pagination.total'))->toBe(1, 'cancel must delete nothing');

    $page->click($delete);
    typeDialogWaitFor($page, "visible('#deleteTypeModal')");
    typeDialogShown($page, 'deleteTypeModal');
    $page->assertAttributeContains('#deleteTypeModal [data-dialog-confirm]', 'class', 'btn-danger');
    $page->click('#deleteTypeModal [data-dialog-confirm]');
    typeDialogWaitFor($page, "!visible('#deleteTypeModal')");

    expect($this->getJson('/api/product-types/')->json('pagination.total'))->toBe(0);
});
