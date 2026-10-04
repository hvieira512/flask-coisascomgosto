<?php

/*
 * The dashboard's chrome at phone width. Everything here was reported by the
 * owners on a phone: the user's dropdown drawn outside the bar, the burger
 * stranded mid-bar, and a modal whose body pushed past the dialog so the page
 * scrolled behind it instead.
 */

const MOBILE_WIDTH = 390;

beforeEach(function () {
    signIn(makeUser('phone'));
    $product = makeProduct('Caixa Redonda');

    // Real colour names, because that is what a card has to fit: on one line the
    // chips truncated to "Branco …", which names no colour.
    foreach (['Branco e Dourado', 'Preto e Dourado', 'Vermelho e Branco'] as $name) {
        makeVariant($product, makeColorSet($name, [makeColor("Cor {$name}")['id']]));
    }
});

// The browser is not up yet in beforeEach, so each test opens the page itself.
function mobilePhone()
{
    $page = visit('/dashboard/products')->resize(MOBILE_WIDTH, 780);
    $page->page()->waitForSelector('#product-list tr[data-product-id] >> nth=0');

    return $page;
}

// Page::waitForFunction builds the request but never sends it, so poll here.
function mobileWaitUntil($page, string $condition): void
{
    $met = $page->script("new Promise(resolve => { const end = Date.now() + 5000; (function poll() { if ({$condition}) return resolve(true); if (Date.now() > end) return resolve(false); setTimeout(poll, 50); })(); })");
    expect($met)->toBeTrue("timed out waiting for: {$condition}");
}

function mobileOpenEditor($page): void
{
    $page->script("document.querySelector('#product-list tr[data-product-id]').click()");
    $page->page()->waitForSelector('#editProductModal', ['state' => 'visible']);
}

describe('the navbar', function () {
    // Bootstrap's navbar is a row at every width; under Bulma the user's control
    // was drawn under the 52px bar rather than in it.
    it('keeps everything inside the bar', function () {
        $page = mobilePhone();
        $state = $page->script(<<<'JS'
            () => {
                const bar = document.querySelector('.dash-navbar').getBoundingClientRect();
                const user = document.querySelector('[data-dropdown-trigger]').getBoundingClientRect();
                const burger = document.getElementById('sidebarToggle').getBoundingClientRect();
                return {
                    barBottom: Math.round(bar.bottom),
                    userBottom: Math.round(user.bottom),
                    burgerBottom: Math.round(burger.bottom),
                };
            }
            JS);

        expect($state['userBottom'])->toBeLessThanOrEqual($state['barBottom'] + 1)
            ->and($state['burgerBottom'])->toBeLessThanOrEqual($state['barBottom'] + 1);
        $page->assertNoJavaScriptErrors();
    });

    // It used to hide the username below 992px, so on a phone the dashboard never
    // said whose it was.
    it('says who is signed in', function () {
        $page = mobilePhone();
        $state = $page->script(<<<'JS'
            () => {
                const name = document.querySelector('.dash-user-name');
                return {
                    text: name.textContent.trim(),
                    width: Math.round(name.getBoundingClientRect().width),
                    display: getComputedStyle(name).display,
                };
            }
            JS);

        expect($state['text'])->toBe('phone')
            ->and($state['width'])->toBeGreaterThan(0)
            ->and($state['display'])->not->toBe('none');
    });

    // The bar truncates a long name, so the dropdown is where it is readable.
    it('carries the name in full in the menu', function () {
        $page = mobilePhone();
        $page->click('[data-dropdown-trigger]');
        $page->page()->waitForSelector('.dropdown-menu.show');

        expect(trim($page->text('.dropdown-menu.show .dropdown-header')))->toBe('phone');
    });

    // A fixed-height .navbar wraps by default, and what did not fit dropped onto a
    // second line the bar then clipped.
    it('lets a long name give way instead of breaking the bar', function () {
        $page = mobilePhone();
        $page->script("document.querySelector('.dash-user-name').textContent = 'mariajoaodecarvalhoesilva'");
        $state = $page->script(<<<'JS'
            () => {
                const name = document.querySelector('.dash-user-name');
                const burger = document.getElementById('sidebarToggle').getBoundingClientRect();
                const where = document.querySelector('.dash-where').getBoundingClientRect();
                return {
                    truncated: name.scrollWidth > name.clientWidth + 1,
                    burgerLeft: Math.round(burger.left),
                    onOneLine: burger.top < where.bottom
                        && where.top < burger.bottom
                        && where.left >= burger.right - 1,
                };
            }
            JS);

        expect($state['truncated'])->toBeTrue('the name should ellipsize, not push')
            ->and($state['burgerLeft'])->toBeLessThan(24)
            ->and($state['onOneLine'])->toBeTrue('the bar wrapped onto a second line');
    });

    // The rail is an offcanvas-start drawer, so its control sits on the edge it
    // comes from; the user's menu keeps the right.
    it('puts the burger against the left edge', function () {
        $page = mobilePhone();
        $state = $page->script(<<<'JS'
            () => ({
                burgerLeft: Math.round(document.getElementById('sidebarToggle').getBoundingClientRect().left),
                userRight: Math.round(document.querySelector('[data-dropdown-trigger]').getBoundingClientRect().right),
                viewport: window.innerWidth,
            })
            JS);

        expect($state['burgerLeft'])->toBeLessThan(24)
            ->and($state['viewport'] - $state['userRight'])->toBeLessThan(24);
    });

    // It used to be clipped out of existence by the fixed bar's own overflow: a box,
    // opacity 1, and absent from elementsFromPoint.
    it('opens the dropdown below the bar and on top', function () {
        $page = mobilePhone();
        $page->click('[data-dropdown-trigger]');
        $page->page()->waitForSelector('.dropdown-menu.show');

        $state = $page->script(<<<'JS'
            () => {
                const menu = document.querySelector('.dropdown-menu.show');
                const box = menu.getBoundingClientRect();
                const bar = document.querySelector('.dash-navbar').getBoundingClientRect();
                const trigger = document.querySelector('[data-dropdown-trigger]').getBoundingClientRect();
                const top = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
                return {
                    hasSize: box.height > 0,
                    belowTheTrigger: box.top >= trigger.bottom - 2,
                    insideTheBarsWidth: box.top < bar.bottom + 24,
                    withinViewport: box.right <= window.innerWidth && box.left >= 0,
                    isOnTop: menu.contains(top),
                };
            }
            JS);

        expect($state['hasSize'])->toBeTrue('the dropdown has no box')
            ->and($state['isOnTop'])->toBeTrue('something is painted over the dropdown')
            ->and($state['belowTheTrigger'])->toBeTrue()
            ->and($state['insideTheBarsWidth'])->toBeTrue()
            ->and($state['withinViewport'])->toBeTrue();
    });

    // The offcanvas brings its own backdrop, so there is no #overlay of ours.
    it('opens the sidebar from the burger', function () {
        $page = mobilePhone();
        $page->click('#sidebarToggle');
        $page->page()->waitForSelector('#sidebar.show');
        // The class lands before the slide-in runs, so the box is still off-screen.
        mobileWaitUntil($page, "document.getElementById('sidebar').getBoundingClientRect().x >= -1");

        $page->assertCount('.offcanvas-backdrop', 1)
            ->assertCount('#sidebar [aria-current]', 1);
    });
});

// It was a 56rem table in a wrapper that scrolled sideways, and the only way to
// reach Apagar on a phone was to drag the table and hope. The markup is still a
// table, so this is CSS, and every dashboard listing becomes cards from it.
describe('a record is a card', function () {
    // A header row above one column of cards labels nothing; it was also sticky,
    // pinned on top of the first piece.
    it('drops the column header', function () {
        expect(mobilePhone()->script("getComputedStyle(document.querySelector('.dash-table thead')).display"))->toBe('none');
    });

    // The honest test is trying to move it: documentElement.scrollWidth counts
    // descendant scrollports and reported 524px on a page that cannot move.
    it('does not scroll the page sideways', function () {
        $page = mobilePhone();
        $page->script('window.scrollTo(300, 0)');

        expect($page->script('window.scrollX'))->toBe(0);
    });

    it('leaves the records wrapper nothing to scroll', function () {
        $overflow = mobilePhone()->script(<<<'JS'
            () => {
                const wrap = document.querySelector('.dash-table-wrap');
                return wrap.scrollWidth - wrap.clientWidth;
            }
            JS);

        expect($overflow)->toBeLessThanOrEqual(1);
    });

    it('keeps every action on screen', function () {
        $offscreen = mobilePhone()->script(<<<'JS'
            () => [...document.querySelectorAll('#product-list tr [data-product-action]')]
                .filter(button => {
                    const box = button.getBoundingClientRect();
                    return box.right > window.innerWidth + 1 || box.left < 0 || box.width === 0;
                }).length
            JS);

        expect($offscreen)->toBe(0);
    });

    // Revealed on hover on a real screen. `@media (hover: none)` describes the
    // device, not the width: a narrow laptop window still reports a mouse.
    it('shows the actions without a hover', function () {
        expect(mobilePhone()->script("getComputedStyle(document.querySelector('#product-list tr .dash-row-actions')).opacity"))->toBe('1');
    });

    it('is a card and not a row', function () {
        $shape = mobilePhone()->script(<<<'JS'
            () => {
                const row = document.querySelector('#product-list tr');
                const style = getComputedStyle(row);
                const box = row.getBoundingClientRect();
                return {
                    display: style.display,
                    borderWidth: parseFloat(style.borderTopWidth),
                    radius: parseFloat(style.borderTopLeftRadius),
                    width: Math.round(box.width),
                };
            }
            JS);

        expect($shape['display'])->toBe('flex')
            ->and($shape['borderWidth'])->toBeGreaterThanOrEqual(1)
            ->and($shape['radius'])->toBeGreaterThan(0)
            ->and($shape['width'])->toBeLessThanOrEqual(MOBILE_WIDTH);
    });

    // On one line three chips came out "Branco …", "Preto …", "Preto …".
    it('does not truncate the colour names to nothing', function () {
        $page = mobilePhone();
        $page->page()->waitForSelector('#product-list .color-set-name >> nth=0');

        $clipped = $page->script("[...document.querySelectorAll('#product-list .color-set-name')].filter(el => el.scrollWidth > el.clientWidth + 1).length");

        expect($clipped)->toBe(0);
    });

    it('still opens the editor on a tap', function () {
        $page = mobilePhone();
        $page->click('#product-list tr[data-product-id] >> nth=0');

        $page->page()->waitForSelector('#editProductModal.show');
        $page->assertVisible('#editProductModal');
    });
});

describe('the modal scrolls its own body', function () {
    // The max-height was on the <dialog>, which capped nothing inside it: the
    // colours panel came out 1028px tall in a 732px dialog.
    it('scrolls a tall panel inside the dialog', function () {
        $page = mobilePhone();
        mobileOpenEditor($page);
        $page->click('#edit-tabs li[data-tab="variants"] .nav-link');

        $state = $page->script(<<<'JS'
            () => {
                const dialog = document.getElementById('editProductModal');
                const body = dialog.querySelector('.modal-body');
                return {
                    bodyWithinDialog: body.getBoundingClientRect().height <= dialog.getBoundingClientRect().height,
                    bodyOverflow: getComputedStyle(body).overflowY,
                    // Bootstrap locks the scroll on <body>, not on <html>.
                    pageLocked: getComputedStyle(document.body).overflow,
                    modalOpen: document.body.classList.contains('modal-open'),
                };
            }
            JS);

        expect($state['bodyWithinDialog'])->toBeTrue('the body is taller than the dialog holding it')
            ->and($state['bodyOverflow'])->toBe('auto')
            ->and($state['modalOpen'])->toBeTrue()
            ->and($state['pageLocked'])->toBe('hidden');
    });

    it('lets the page scroll again once it closes', function () {
        $page = mobilePhone();
        mobileOpenEditor($page);
        // Escape is handled on the modal element, so it has to hold focus first.
        mobileWaitUntil($page, "document.getElementById('editProductModal').contains(document.activeElement)");
        $page->keys(':focus', 'Escape');
        $page->page()->waitForSelector('#editProductModal', ['state' => 'hidden']);
        // The lock lifts once the backdrop has faded, after the modal is hidden.
        mobileWaitUntil($page, "!document.body.classList.contains('modal-open')");

        expect($page->script('getComputedStyle(document.body).overflow'))->not->toBe('hidden');
        $page->assertCount('.modal-backdrop', 0);
    });
});
