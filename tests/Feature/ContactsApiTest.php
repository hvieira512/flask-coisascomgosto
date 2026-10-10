<?php

use App\Support\Format;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

beforeEach(fn () => signIn());

function contactsSection(): string
{
    $html = test()->get('/')->getContent();
    $start = strpos($html, 'id="contacts"');

    return substr($html, $start, strpos($html, '</section>', $start) - $start);
}

/** Drop screen-reader-only spans, then all tags, leaving what is seen. */
function contactsVisibleText(string $markup): string
{
    $markup = preg_replace('#<span class="visually-hidden">.*?</span>#s', '', $markup);

    return preg_replace('/<[^>]+>/', ' ', $markup);
}

describe('the contacts API', function () {
    it('serves the seeded contact details', function () {
        $this->getJson('/api/contacts/')
            ->assertJsonPath('address', 'Viana do Castelo, Portugal')
            ->assertJsonPath('email', 'geral@coisascomgosto.pt');
    });

    it('seeds the socials', function () {
        $body = $this->getJson('/api/contacts/')->json();

        expect($body['facebook_url'])->toContain('facebook.com')
            ->and($body['instagram_url'])->toContain('instagram.com');
    });

    it('derives the WhatsApp URL from the number', function () {
        $this->getJson('/api/contacts/')
            ->assertJsonPath('whatsapp', '939320334')
            ->assertJsonPath('whatsapp_url', 'https://wa.me/939320334');
    });

    // The WhatsApp number is the phone number, by design.
    it('has no separate phone field', function () {
        expect($this->getJson('/api/contacts/')->json())->not->toHaveKey('phone');
    });

    it('replaces the details on update', function () {
        $this->putJson('/api/contacts/', [
            'address' => 'Rua Nova 1, Viana do Castelo',
            'email' => 'loja@example.com',
            'whatsapp' => '+351 912 345 678',
            'facebook_url' => 'https://facebook.com/x',
            'instagram_url' => 'https://instagram.com/x',
        ])->assertOk()->assertJsonPath('address', 'Rua Nova 1, Viana do Castelo');
    });

    it('strips spaces and the plus from the WhatsApp URL', function () {
        $this->putJson('/api/contacts/', ['whatsapp' => '+351 912 345 678']);

        $this->getJson('/api/contacts/')->assertJsonPath('whatsapp_url', 'https://wa.me/351912345678');
    });

    it('yields no WhatsApp URL for a blank number', function () {
        $this->putJson('/api/contacts/', ['address' => 'Só morada']);

        $this->getJson('/api/contacts/')->assertJsonPath('whatsapp_url', null);
    });

    it('treats an update as a full replacement', function () {
        $this->putJson('/api/contacts/', ['email' => 'novo@example.com']);

        $this->getJson('/api/contacts/')
            ->assertJsonPath('email', 'novo@example.com')
            ->assertJsonPath('address', null);
    });

    it('stays a singleton', function () {
        $this->putJson('/api/contacts/', ['email' => 'a@example.com']);
        $this->putJson('/api/contacts/', ['email' => 'b@example.com']);

        expect(DB::table('contacts')->count())->toBe(1);
    });
});

describe('the landing page', function () {
    it('renders at the root', function () {
        $this->get('/')->assertOk()->assertSee('Coisas com Gosto', false);
    });

    it('leads with the pieces, then tells the story', function () {
        makeProductType('Caixa');
        $html = $this->get('/')->getContent();

        // Each section's own heading, not the navbar links or the hero's CTA,
        // which share the same words.
        $positions = array_map(fn ($h) => strpos($html, $h), [
            'O que sai da oficina',
            'Começou numa bancada pequena',
            'três mãos-cheias de tempo',
            'Onde nos encontra</h2>',
        ]);
        expect($positions)->not->toContain(false);
        $sorted = $positions;
        sort($sorted);
        expect($positions)->toBe($sorted);
    });

    it('shows the range before the workshop story', function () {
        makeProductType('Caixa');
        $html = $this->get('/')->getContent();

        expect(strpos($html, 'O que sai da oficina'))->toBeLessThan(strpos($html, 'id="origem"'));
    });

    it('keeps the contacts in a section, not the navbar', function () {
        $html = $this->get('/')->getContent();
        $navStart = strpos($html, '<nav');
        $navbar = substr($html, $navStart, strpos($html, '</nav>') - $navStart);

        expect($navbar)->not->toContain('wa.me')
            ->and($html)->toContain('id="contacts"');
    });

    it('sets the contacts as type, not cards', function () {
        $contacts = contactsSection();

        expect($contacts)->not->toContain('card')
            ->not->toContain('contact-icon')
            ->toContain('font-display');
    });

    it('closes on the one dark band, the contacts', function () {
        $html = $this->get('/')->getContent();

        expect(substr_count($html, 'data-bs-theme="dark"'))->toBe(1)
            ->and(strpos($html, 'id="contacts"'))->toBeLessThan(strpos($html, '<footer'));
    });

    it('keeps every family tile on one baseline', function () {
        makeProductType('Caixa');

        $this->get('/')->assertSee('--bs-aspect-ratio: 125%', false);
    });

    it('shows the contact values, not just the labels', function () {
        $visible = contactsVisibleText(contactsSection());

        expect($visible)->toContain('geral@coisascomgosto.pt')->toContain('939320334');
    });

    it('shows the social handle, not the URL', function () {
        $visible = contactsVisibleText(contactsSection());

        expect($visible)->toContain('coisascomgosto.vianadocastelo')
            ->not->toContain('https://www.instagram.com');
    });

    // The address carries no label: it is the display line the block opens with.
    it('keeps the labels visible', function () {
        $visible = contactsVisibleText(contactsSection());

        foreach (['E-mail', 'WhatsApp', 'Facebook', 'Instagram', 'Viana do Castelo'] as $text) {
            expect($visible)->toContain($text);
        }
    });

    it('links the address to the map', function () {
        expect(contactsSection())->toContain('https://maps.app.goo.gl/bAYkhcE3gvaKDw5W9')->toContain('rel="noopener"');
    });

    // PUT is a full replacement, so omitting maps_url is how it is cleared.
    it('renders the address as plain text without a map link', function () {
        $this->putJson('/api/contacts/', ['address' => 'Viana do Castelo']);

        expect(contactsSection())->not->toContain('maps.app.goo.gl')
            ->not->toContain('Ver no mapa')
            ->toContain('Viana do Castelo');
    });

    it('has a reserved-area link instead of Entrar', function () {
        $this->get('/')->assertSee('Área reservada', false)->assertDontSee('>Entrar<', false);
    });

    it('is styled by Bootstrap alone', function () {
        $this->get('/')->assertSee('bootstrap/bootstrap.min.css', false)->assertDontSee('bulma', false);
    });

    it('shows the logo in the navbar', function () {
        $this->get('/')->assertSee('img/logo.png', false)->assertSee('navbar-brand', false)->assertSee('font-display', false);
    });

    it('renders the contact details', function () {
        $this->get('/')
            ->assertSee('geral@coisascomgosto.pt', false)
            ->assertSee('wa.me/939320334', false)
            ->assertSee('facebook.com/coisascomgosto.vianadocastelo', false);
    });

    it('lists the product types', function () {
        makeProductType('Caixa redonda');

        $this->get('/')->assertSee('Caixa redonda', false);
    });

    it('links each type to the filtered catalogue', function () {
        $type = makeProductType('Moldura');

        $this->get('/')->assertSee("/products?type_id={$type['id']}", false);
    });

    it('links each type card from the range section', function () {
        $type = makeProductType('Coracao');
        $html = $this->get('/')->getContent();
        $start = strpos($html, 'As peças');

        expect(substr($html, $start, strpos($html, 'id="contacts"') - $start))->toContain("/products?type_id={$type['id']}");
    });

    it('omits the range section on an empty catalogue', function () {
        $this->get('/')->assertOk()
            ->assertDontSee('O que sai da oficina', false)
            ->assertSee('id="origem"', false)
            ->assertSee('id="contacts"', false);
    });
});

describe('error pages', function () {
    it('answers an unknown page with the custom 404', function () {
        $this->get('/not-found')->assertNotFound()->assertSee('Página não encontrada', false)->assertSee('404', false);
    });

    it('keeps the site chrome on the 404', function () {
        $this->get('/not-found')->assertSee('bootstrap/bootstrap.min.css', false)->assertSee('Coisas com Gosto', false);
    });

    // The shell renders; the page's JS shows the error state.
    it('renders the product page shell for an unknown product', function () {
        $this->get('/products/9999')->assertOk();
    });

    it('keeps an API 404 as JSON', function () {
        expect($this->get('/api/not-found')->assertNotFound()->headers->get('Content-Type'))->toStartWith('application/json');
    });

    it('keeps an API resource 404 as JSON', function () {
        expect($this->get('/api/products/9999')->assertNotFound()->headers->get('Content-Type'))->toStartWith('application/json');
    });
});

describe('the dashboard contacts page', function () {
    it('has an input for every field', function () {
        $page = $this->get('/dashboard/contacts');

        foreach (['address', 'maps_url', 'email', 'whatsapp', 'facebook_url', 'instagram_url'] as $name) {
            $page->assertSee("id=\"cf-{$name}\"", false);
        }
    });

    it('loads its module', function () {
        $this->get('/dashboard/contacts')->assertSee('js/dashboard/contacts.js', false)->assertSee('id="contact-form"', false);
    });

    it('is in the sidebar', function () {
        $this->get('/dashboard/contacts')->assertSee('/dashboard/contacts', false)->assertSee('Contactos', false);
    });
});

describe('update semantics', function () {
    it('clears a field that is omitted', function () {
        $this->putJson('/api/contacts/', ['address' => 'Só morada']);

        $this->getJson('/api/contacts/')
            ->assertJsonPath('address', 'Só morada')
            ->assertJsonPath('instagram_url', null);
    });

    it('keeps every field that is sent', function () {
        $payload = [
            'address' => 'Rua de Cardielos, n. 222',
            'email' => 'geral@coisascomgosto.pt',
            'whatsapp' => '939320334',
            'maps_url' => 'https://maps.app.goo.gl/x',
            'facebook_url' => 'https://facebook.com/x',
            'instagram_url' => 'https://instagram.com/x',
        ];
        $this->putJson('/api/contacts/', $payload);

        expect($this->getJson('/api/contacts/')->json())->toMatchArray($payload);
    });

    // The dashboard shows this preview, so it must match the API.
    it('derives the WhatsApp URL from a spaced number', function () {
        $this->putJson('/api/contacts/', ['whatsapp' => '+351 939 320 334']);

        $this->getJson('/api/contacts/')->assertJsonPath('whatsapp_url', 'https://wa.me/351939320334');
    });
});

describe('socialHandle', function () {
    it('reduces a profile URL to the handle', function (?string $url, ?string $handle) {
        expect(Format::socialHandle($url))->toBe($handle);
    })->with([
        'instagram URL' => ['https://www.instagram.com/coisascomgosto.vianadocastelo/', 'coisascomgosto.vianadocastelo'],
        'facebook URL without a trailing slash' => ['https://www.facebook.com/coisascomgosto.vianadocastelo', 'coisascomgosto.vianadocastelo'],
        'nested path takes the last segment' => ['https://facebook.com/pages/loja', 'loja'],
        'a bare handle passes through' => ['coisascomgostovc', 'coisascomgostovc'],
        // Better a visible URL than an empty card.
        'a domain with no path falls back to the URL' => ['https://facebook.com', 'https://facebook.com'],
        'null stays null' => [null, null],
    ]);
});

// Only the table-does-not-exist case is tolerated — the gap between a clone and
// the first migration. Anything else must reach the owners.
describe('contact injection', function () {
    it('renders pages before the table exists', function () {
        Schema::rename('contacts', 'contacts_aside');
        try {
            $this->get('/')->assertOk()->assertSee('Coisas com Gosto', false);
        } finally {
            Schema::rename('contacts_aside', 'contacts');
        }
    });

    it('does not hide a real database failure', function () {
        DB::beforeExecuting(function (string $query) {
            if (str_contains($query, '`contacts`')) {
                throw new PDOException("SQLSTATE[HY000] [2002] Can't connect to MySQL server");
            }
        });

        $this->withoutExceptionHandling();
        expect(fn () => $this->get('/'))->toThrow(Exception::class);
    });
});
