<?php

/*
 * Filtering the catalogue without a mouse. The sidebar entries were <a>s with
 * no href — not focusable, not announced — while the badges that remove the same
 * filters were buttons: a keyboard user could undo a filter they could never
 * apply. They add up, so they are checkboxes (aria-checked), not toggle buttons.
 */

beforeEach(fn () => signIn());

/** The grid is refetched when a filter changes, so counting straight after a keypress counts the old grid. */
function keyboardWaitForCards($page, int $count): void
{
    waitUntil($page, "document.querySelectorAll('#product-grid .product-card').length === {$count}");
}

function keyboardEntry(string $name): string
{
    return ".filter-entry:has-text(\"{$name}\") >> nth=0";
}

/** Two types with pieces, so there is more than one thing to tick. */
function keyboardCatalogue()
{
    $box = makeProductType('Caixa');
    $frame = makeProductType('Moldura');
    makeProduct('Caixa Redonda', typeId: $box['id']);
    makeProduct('Caixa de Joias', typeId: $box['id']);
    makeProduct('Moldura Oval', typeId: $frame['id']);

    $page = visit('/products')->resize(1280, 900);
    waitUntil($page, "document.querySelector('.filter-entry') !== null");

    return $page;
}

/**
 * Tab from the search box until a filter entry has focus. Real key presses
 * rather than .focus(): only keyboard interaction makes :focus-visible match.
 */
function keyboardFocusByTab($page, int $limit = 40): void
{
    $page->keys('#filter-search', 'Tab');
    for ($i = 0; $i < $limit; $i++) {
        if ($page->script("document.activeElement?.classList.contains('filter-entry')")) {
            return;
        }
        $page->keys(':focus', 'Tab');
    }
    test()->fail("{$limit} tabs from the search box and no filter was reached");
}

describe('the entries are reachable', function () {
    it('makes every entry with pieces focusable', function () {
        $tabindexes = keyboardCatalogue()->script("[...document.querySelectorAll('.filter-entry:not(.is-empty)')].map(el => el.getAttribute('tabindex'))");

        expect($tabindexes)->not->toBeEmpty('no filter entries rendered')
            ->and(array_unique($tabindexes))->toBe(['0']);
    });

    // Listed, as part of the workshop's vocabulary, but ticking it could only empty the grid.
    it('skips an entry with nothing behind it', function () {
        makeProductType('Tipo vazio');
        makeProduct('Uma peça');

        $page = visit('/products');
        waitUntil($page, "document.querySelector('.filter-entry') !== null");

        $page->assertAttribute('.filter-entry.is-empty >> nth=0', 'tabindex', '-1')
            ->assertAttribute('.filter-entry.is-empty >> nth=0', 'aria-disabled', 'true');
    });

    it('is reached by pressing Tab, not merely focusable', function () {
        $page = keyboardCatalogue();

        keyboardFocusByTab($page);

        expect($page->script("document.activeElement.getAttribute('role')"))->toBe('checkbox');
    });
});

describe('it announces itself as a checkbox', function () {
    it('carries the role and state', function () {
        keyboardCatalogue()
            ->assertAttribute('.filter-entry >> nth=0', 'role', 'checkbox')
            ->assertAttribute('.filter-entry >> nth=0', 'aria-checked', 'false');
    });

    it('updates the state when ticked', function () {
        $page = keyboardCatalogue();

        $page->click(keyboardEntry('Caixa'));
        waitUntil($page, "document.querySelector('.filter-entry.is-active') !== null");

        $page->assertAttribute(keyboardEntry('Caixa'), 'aria-checked', 'true');
    });

    // aria-pressed would say "one of these, on or off"; these add up.
    it('is not a toggle button', function () {
        keyboardCatalogue()->assertCount('.filter-entry[aria-pressed]', 0);
    });
});

describe('the keyboard does what the mouse does', function () {
    it('ticks the focused entry with Space', function () {
        $page = keyboardCatalogue();
        keyboardWaitForCards($page, 3);

        $page->keys(keyboardEntry('Caixa'), 'Space');
        keyboardWaitForCards($page, 2);

        $page->assertAttribute(keyboardEntry('Caixa'), 'aria-checked', 'true')
            ->assertNoJavaScriptErrors();
    });

    it('unticks it with Space again', function () {
        $page = keyboardCatalogue();
        $page->keys(keyboardEntry('Caixa'), 'Space');
        waitUntil($page, "document.querySelector('.filter-entry.is-active') !== null");

        $page->keys(':focus', 'Space');
        keyboardWaitForCards($page, 3);

        $page->assertAttribute(keyboardEntry('Caixa'), 'aria-checked', 'false');
    });

    // Not required of a checkbox, but it is what a keyboard user tries on something that looks like a link.
    it('ticks with Enter too', function () {
        $page = keyboardCatalogue();

        $page->keys(keyboardEntry('Moldura'), 'Enter');
        keyboardWaitForCards($page, 1);

        $page->assertAttribute(keyboardEntry('Moldura'), 'aria-checked', 'true');
    });

    // Space's default is a page-down, which would take the sidebar out from under its user.
    it('does not scroll the page on Space', function () {
        $page = keyboardCatalogue();

        $page->keys(keyboardEntry('Caixa'), 'Space');
        waitUntil($page, "document.querySelector('.filter-entry.is-active') !== null");

        expect($page->script('window.scrollY'))->toBe(0);
    });

    it('lets two be ticked at once', function () {
        $page = keyboardCatalogue();

        $page->keys(keyboardEntry('Caixa'), 'Space');
        waitUntil($page, "document.querySelector('.filter-entry.is-active') !== null");
        $page->keys(keyboardEntry('Moldura'), 'Space');
        waitUntil($page, "document.querySelectorAll('.filter-entry.is-active').length === 2");
        keyboardWaitForCards($page, 3);

        $page->assertAttribute(keyboardEntry('Caixa'), 'aria-checked', 'true')
            ->assertAttribute(keyboardEntry('Moldura'), 'aria-checked', 'true');
    });

    // getComputedStyle takes a pseudo-element, not a pseudo-class, so the ring is read off the focused element.
    it('shows a focused entry visibly focused', function () {
        $page = keyboardCatalogue();

        keyboardFocusByTab($page);

        expect($page->script('getComputedStyle(document.activeElement).boxShadow'))
            ->not->toBeEmpty()->not->toBe('none');
    });
});
