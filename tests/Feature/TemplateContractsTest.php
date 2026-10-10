<?php

/*
 * The element ids the front-end JavaScript queries. A template rewrite once
 * dropped id="form-header" and id="auth-container": the HTML was still valid,
 * and only the browser knew the login page was broken. Each block names the
 * script that would break.
 */

function templateContractsMain(string $html): string
{
    expect(preg_match('#<main[^>]*>(.*?)</main>#s', $html, $match))->toBe(1);

    return $match[1];
}

/** @return list<string> */
function templateContractsSources(string $dir): array
{
    $files = [];
    $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator(base_path($dir), FilesystemIterator::SKIP_DOTS));
    foreach ($iterator as $file) {
        if (fnmatch('*.js', $file->getFilename())) {
            $files[] = $file->getPathname();
        }
    }
    sort($files);

    return $files;
}

function templateContractsRead(string $path): string
{
    return file_get_contents(base_path($path));
}

describe('the login page (js/auth/auth.js)', function () {
    it('has the hooks auth.js renders into', function () {
        $this->get('/auth')->assertOk()
            ->assertSee('id="form-header"', false)
            ->assertSee('id="auth-container"', false)
            ->assertSee('id="auth-form"', false)
            ->assertSee('id="usernameField"', false)
            ->assertSee('id="submitBtn"', false)
            ->assertSee('js/auth/auth.js', false);
    });

    it('loads no token helper: signing in sets a cookie', function () {
        $this->get('/auth')->assertDontSee('js/core/auth.js', false);
    });
});

describe('the dashboard chrome', function () {
    beforeEach(fn () => signIn());

    it('makes the sidebar an offcanvas the burger opens', function () {
        // Bootstrap's offcanvas brings its own backdrop, so there is no #overlay.
        $this->get('/dashboard/home')
            ->assertSee('id="sidebar"', false)
            ->assertSee('id="sidebarToggle"', false)
            ->assertSee('class="offcanvas-lg offcanvas-start dash-sidebar"', false)
            ->assertSee('data-bs-target="#sidebar"', false)
            ->assertDontSee('id="overlay"', false);
    });

    it('has the product list container fetch.js renders into', function () {
        $this->get('/dashboard/products')->assertSee('id="product-list"', false);
    });

    it("uses Bootstrap's modals, opened by our code rather than data-bs-toggle", function () {
        // A form needs the record it edits before it is any use, so opening is ours.
        $this->get('/dashboard/products')
            ->assertSee('class="modal fade dash-modal"', false)
            ->assertSee('class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable"', false)
            ->assertSee('data-bs-dismiss="modal"', false)
            ->assertDontSee('data-bs-toggle="modal"', false)
            ->assertDontSee('<dialog', false);
    });

    it('wires no chrome by hand', function () {
        $this->get('/dashboard/products')->assertDontSee('js/dashboard/menus.js', false);
        expect(file_exists(base_path('public/static/js/dashboard/menus.js')))->toBeFalse();
    });

    it('gives the close control an accessible name', function () {
        $this->get('/dashboard/products')
            ->assertSee('class="btn-close"', false)
            ->assertSee('aria-label="Fechar"', false);
    });

    it('loads no token helper', function () {
        $this->get('/dashboard/products')->assertDontSee('js/core/auth.js', false);
    });

    it('ends the rail with the way back to the storefront', function () {
        $this->get('/dashboard/products')
            ->assertSee('Ver a loja')
            ->assertSee('class="mt-auto px-2 pt-4"', false);
    });

    it('sticks the bar over the work rather than over the rail', function () {
        $this->get('/dashboard/products')
            ->assertSee('class="navbar dash-navbar', false)
            ->assertDontSee('fixed-top', false);

        $css = templateContractsRead('public/static/css/dashboard.css');
        expect($css)->toContain('--dash-navbar-height:')
            ->not->toContain('padding-top: var(--dash-navbar-height)');
    });
});

describe('the storefront (js/store/*.js)', function () {
    it('has the catalogue hooks', function () {
        $response = $this->get('/products');
        foreach (['product-grid', 'active-filters', 'filter-groups', 'filter-search', 'clear-filters', 'pagination'] as $id) {
            $response->assertSee("id=\"{$id}\"", false);
        }
    });

    it('has the product page gallery hooks', function () {
        signIn();
        $product = makeProduct('Caixa');

        $response = $this->get("/products/{$product['id']}");
        foreach (['gallery-stage', 'stage-image', 'thumb-strip', 'stage-counter', 'stage-zoom', 'variant-options', 'size-options'] as $id) {
            $response->assertSee("id=\"{$id}\"", false);
        }
    });
});

// The base layout renders <main> bare for the landing page's full-bleed bands,
// so inner pages bring their own wrapper or the sidebar sits on the viewport edge.
describe('inner pages wrap their content', function () {
    it('wraps the catalogue', function () {
        expect(templateContractsMain($this->get('/products')->getContent()))
            ->toContain('class="section')->toContain('class="container');
    });

    it('wraps the product page', function () {
        signIn();
        $product = makeProduct('Caixa');

        expect(templateContractsMain($this->get("/products/{$product['id']}")->getContent()))
            ->toContain('class="section')->toContain('class="container');
    });

    it('wraps the error page', function () {
        expect(templateContractsMain($this->get('/not-found')->getContent()))
            ->toContain('class="section')->toContain('class="container');
    });
});

describe('notifications (js/core/notify.js wraps SweetAlert2)', function () {
    it('loads SweetAlert2 on the login page', function () {
        $this->get('/auth')->assertSee('sweetalert2/sweetalert2.all.min.js', false);
    });

    it('loads SweetAlert2 on the dashboard', function () {
        signIn();
        $this->get('/dashboard/products')->assertSee('sweetalert2/sweetalert2.all.min.js', false);
    });

    it('imports notify.js rather than loading it', function () {
        $this->get('/auth')->assertDontSee('js/core/notify.js', false);
        expect(templateContractsRead('public/static/js/auth/auth.js'))->toContain('import { Notify }');
    });

    it('reads Swal lazily', function () {
        // A module may run before the classic vendor script has been parsed.
        expect(templateContractsRead('public/static/js/core/notify.js'))->toContain('typeof Swal === "undefined"');
    });

    it('keeps the 77KB library off the storefront', function (string $path) {
        $this->get($path)->assertDontSee('sweetalert2', false);
    })->with(['/', '/products', '/not-found']);
});

// Bootstrap 5.3 carries a dark palette; the shop's paper palette has none.
describe('the light colour scheme', function () {
    it('is pinned on the public pages', function (string $path) {
        $this->get($path)->assertSee('data-bs-theme="light"', false);
    })->with(['/', '/products', '/auth', '/not-found']);

    it('is pinned on the product page', function () {
        signIn();
        $product = makeProduct('Caixa');

        $this->get("/products/{$product['id']}")->assertSee('data-bs-theme="light"', false);
    });

    it('is pinned on the dashboard', function () {
        signIn();
        $this->get('/dashboard/home')->assertSee('data-bs-theme="light"', false);
    });
});

describe('colour set badges (js/store/color-set.js)', function () {
    it('is imported by every script that draws one', function () {
        $users = $importers = [];
        foreach (templateContractsSources('public/static/js') as $path) {
            $source = file_get_contents($path);
            if (str_contains($source, 'ColorSet.')) {
                $users[] = $path;
            }
            if (str_contains($source, 'import { ColorSet }')) {
                $importers[] = $path;
            }
        }

        expect($users)->not->toBeEmpty()
            ->and(array_values(array_diff($users, $importers)))->toBe([]);
    });

    it('is no longer a script tag', function () {
        signIn();
        $product = makeProduct('Caixa');

        foreach (['/products', "/products/{$product['id']}"] as $page) {
            $this->get($page)->assertDontSee('js/store/color-set.js', false);
        }
    });

    it('keeps its base rule in the shared stylesheet', function () {
        // The dashboard loads only theme.css; a storefront-only override is allowed.
        expect(templateContractsRead('public/static/css/theme.css'))->toMatch('/^\.swatch\s*\{/m')
            ->and(templateContractsRead('public/static/css/store.css'))->not->toMatch('/^\.swatch\s*\{/m');
    });

    it('gives the catalogue the name and the swatches it renders', function () {
        signIn();
        $color = makeColor('Vermelho', '#B3282D');
        $set = makeColorSet('Vermelho e Branco', [$color['id']]);
        $product = makeProduct('Caixa');
        makeVariant($product, $set);

        $variant = $this->getJson("/api/products/{$product['id']}")->json('variants.0');
        expect($variant['color_set']['name'])->toBe('Vermelho e Branco')
            ->and($variant['color_set']['colors'][0]['hex'])->toBe('#B3282D');
    });
});

describe('dashboard pages', function () {
    beforeEach(fn () => signIn());

    it('has the products page hooks, and loads exactly one script', function () {
        $response = $this->get('/dashboard/products');
        foreach (['product-list', 'product-count', 'new-product', 'newProductModal', 'editProductModal', 'deleteProductModal',
            'filter-q', 'filter-type', 'filter-collection', 'filter-photos', 'filter-clear'] as $id) {
            $response->assertSee("id=\"{$id}\"", false);
        }
        // Rows open straight into the edit modal.
        $response->assertDontSee('id="viewProductModal"', false)
            ->assertSee('type="module" src="/static/js/dashboard/products/main.js"', false)
            ->assertDontSee('js/store/color-set.js', false)
            ->assertDontSee('js/store/placeholder.js', false);
    });

    it('has the home page analytics hooks', function () {
        $response = $this->get('/dashboard/home');
        foreach (['catalogue-line', 'totals', 'most-viewed', 'asked-colors', 'top-filters'] as $id) {
            $response->assertSee("id=\"{$id}\"", false);
        }
        $response->assertSee('js/dashboard/home.js', false)->assertSee('data-days="7"', false);
    });

    it('has the hooks of each section, and a tab for it in the sidebar', function (string $path, array $ids, string $script, string $tab) {
        $response = $this->get($path);
        foreach ($ids as $id) {
            $response->assertSee("id=\"{$id}\"", false);
        }
        $response->assertSee($script, false)->assertSee($path, false)->assertSee($tab, false);
    })->with([
        'types' => ['/dashboard/types',
            ['type-rows', 'type-count', 'new-type', 'material-rows', 'material-count', 'material-form', 'material-name',
                'newTypeModal', 'editTypeModal', 'deleteTypeModal'],
            'js/dashboard/types/main.js', '>Tipos<'],
        'events' => ['/dashboard/events',
            ['event-rows', 'event-count', 'new-event', 'newEventModal', 'editEventModal', 'deleteEventModal'],
            'js/dashboard/events/main.js', 'Feiras'],
        'colours' => ['/dashboard/colors',
            ['set-rows', 'set-count', 'new-set', 'color-rows', 'color-count', 'color-form', 'color-name', 'color-hex',
                'newSetModal', 'editSetModal', 'deleteSetModal', 'editColorModal', 'deleteColorModal'],
            'js/dashboard/colors/main.js', '>Cores<'],
        'collections' => ['/dashboard/collections',
            ['collection-rows', 'collection-count', 'new-collection', 'newCollectionModal', 'editCollectionModal', 'deleteCollectionModal'],
            'js/dashboard/collections/main.js', 'Colecções'],
    ]);
});

describe('the stepped create forms', function () {
    it('declare their groups', function () {
        expect(templateContractsRead('public/static/js/dashboard/products/form.js'))
            ->toContain('data-step="identity"')->toContain('data-step="details"')
            ->and(templateContractsRead('public/static/js/dashboard/events/main.js'))
            ->toContain('data-step="when"')->toContain('data-step="details"');
    });

    it('step through creating but not editing', function () {
        $products = templateContractsRead('public/static/js/dashboard/products/main.js');
        $events = templateContractsRead('public/static/js/dashboard/events/main.js');

        expect($products)->toContain('id: "newProductModal"')->toContain('#edit-tabs')
            ->and(substr_count($products, 'stepDialog({'))->toBe(1)
            ->and(substr_count($events, 'stepDialog({'))->toBe(1)
            ->and(substr_count($events, 'formDialog({'))->toBe(1);
    });

    it('write nothing before the last step', function () {
        expect(templateContractsRead('public/static/js/core/steps.js'))
            ->toContain('if (!last())')->toContain('onFinish(root)');
    });

    it('hide Back with the attribute, which Bootstrap honours', function () {
        expect(templateContractsRead('public/static/js/core/steps.js'))->toContain('back.hidden = index === 0')
            ->and(templateContractsRead('public/static/bootstrap/bootstrap.min.css'))->toContain('[hidden]{display:none!important}');
    });

    it('slide with a reduced-motion escape', function () {
        $css = templateContractsRead('public/static/css/dashboard.css');
        expect($css)->toContain('@keyframes step-in')->toContain('[data-step] {');

        $reduced = array_slice(explode('prefers-reduced-motion: reduce', $css), 1);
        expect(array_filter($reduced, fn ($block) => str_contains($block, '[data-step]')))->not->toBeEmpty();
    });
});

// The create and edit modals share element ids and a closed modal stays in the
// DOM, so reading a field by id alone found the create form.
describe('modal form scoping', function () {
    it('scopes the event form to its modal', function () {
        expect(templateContractsRead('public/static/js/dashboard/events/main.js'))
            ->toContain('submitEventForm(modalId)')
            ->toContain('modal(modalId).querySelector("#event-form")')
            ->not->toContain('document.getElementById("event-form")');
    });

    it('scopes the product form to its modal', function () {
        expect(templateContractsRead('public/static/js/dashboard/products/form.js'))
            ->toContain('root.querySelector("#product-form")')
            ->not->toContain('document.getElementById("product-form")');
    });
});

describe('the product gallery', function () {
    beforeEach(function () {
        signIn();
        $product = makeProduct('Caixa');
        $this->productPage = $this->get("/products/{$product['id']}");
    });

    it('loads exactly one script', function () {
        $this->productPage
            ->assertSee('type="module" src="/static/js/store/product.js"', false)
            ->assertDontSee('js/store/gallery.js', false)
            ->assertDontSee('js/store/lightbox.js', false);
    });

    it('loads the PhotoSwipe stylesheet, which a module cannot import', function () {
        $this->productPage->assertSee('photoswipe/photoswipe.css', false);
    });

    it('imports the lightbox', function () {
        expect(templateContractsRead('public/static/js/store/gallery.js'))
            ->toContain('import { StoreLightbox } from "./lightbox.js"')
            ->not->toContain('window.StoreLightbox');
    });
});

describe('one module system', function () {
    it('publishes nothing on window', function () {
        $offenders = [];
        foreach (templateContractsSources('public/static/js') as $path) {
            foreach (file($path) as $line) {
                // window.Swal is SweetAlert2's own global, read, not written.
                if (preg_match('/^\s*window\.[A-Z]\w*\s*=/', $line)) {
                    $offenders[] = "{$path}: ".trim($line);
                }
            }
        }

        expect($offenders)->toBe([]);
    });

    it('makes every script tag a module, bar the vendored globals', function () {
        // Bootstrap's bundle stays classic so its data-api is wired before any module runs.
        signIn();
        $product = makeProduct('Caixa');

        $pages = ['/', '/products', "/products/{$product['id']}", '/dashboard/home', '/dashboard/products', '/dashboard/types',
            '/dashboard/colors', '/dashboard/collections', '/dashboard/events', '/dashboard/contacts'];

        foreach ($pages as $page) {
            preg_match_all('/<script[^>]*src=[^>]*>/', $this->get($page)->assertOk()->getContent(), $tags);
            foreach ($tags[0] as $tag) {
                if (preg_match('/sweetalert2|fontawesome|bootstrap/', $tag)) {
                    continue;
                }
                expect($tag)->toContain('type="module"');
            }
        }
    });
});

it('carries no template syntax from another language in the markup builders', function () {
    // A Jinja or JSX comment inside a template literal is just text, and renders.
    $offenders = [];
    foreach (templateContractsSources('public/static/js') as $path) {
        $source = file_get_contents($path);
        foreach (['{#', '{/*'] as $opener) {
            if (str_contains($source, $opener)) {
                $offenders[] = "{$path}: {$opener}";
            }
        }
    }

    expect($offenders)->toBe([]);
});

it('reveals row actions on any row, not only a table', function () {
    // Scoped to .dash-table, the materials list kept its buttons at opacity 0.
    expect(templateContractsRead('public/static/css/dashboard.css'))
        ->toContain(':is(tr, li):hover .dash-row-actions')
        ->not->toContain('.dash-table tbody tr:hover .dash-row-actions');
});

it('offers the full materials panel on the types page', function () {
    signIn();
    $response = $this->get('/dashboard/types');
    foreach (['material-form', 'material-name', 'material-rows', 'material-count'] as $id) {
        $response->assertSee("id=\"{$id}\"", false);
    }
});

// A stray "*/" inside a comment once swallowed the .section rule after it, and
// the stylesheet still served with a 200.
describe('the stylesheets parse', function () {
    it('closes every comment exactly once', function () {
        foreach (glob(base_path('public/static/css/*.css')) as $sheet) {
            $text = file_get_contents($sheet);
            expect(substr_count($text, '/*'))->toBe(substr_count($text, '*/'), $sheet);
        }
    });

    it('balances the braces', function () {
        foreach (glob(base_path('public/static/css/*.css')) as $sheet) {
            $text = preg_replace('#/\*.*?\*/#s', '', file_get_contents($sheet));
            expect(substr_count($text, '{'))->toBe(substr_count($text, '}'), $sheet);
        }
    });

    it('keeps the padding on the storefront bands', function () {
        $css = templateContractsRead('public/static/css/theme.css');
        expect(substr($css, strpos($css, '.section {'), 120))->toContain('padding: 3rem 1.5rem');

        $this->get('/')->assertSee('class="section', false);
    });
});
