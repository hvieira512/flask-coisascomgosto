<?php

use App\Support\Format;
use Illuminate\Support\Facades\Auth;

beforeEach(fn () => signIn());

function eventsCreate(string $name = 'Feira de Artesanato', string $startsOn = '2025-08-12', array $fields = []): array
{
    return created('/api/events/', ['name' => $name, 'starts_on' => $startsOn, ...$fields]);
}

function eventsTwo(): void
{
    eventsCreate('Primeira', '2025-08-12');
    eventsCreate('Segunda', '2025-09-12');
}

describe('the events API', function () {
    it('answers an empty page on an empty table', function () {
        $this->getJson('/api/events/')
            ->assertJsonPath('events', [])
            ->assertJsonPath('pagination.total', 0);
    });

    it('reads back what was created', function () {
        $made = eventsCreate('Mostra de Artesanato', '2025-08-12', ['location' => 'Viana do Castelo']);

        $this->getJson("/api/events/{$made['id']}")
            ->assertJsonPath('name', 'Mostra de Artesanato')
            ->assertJsonPath('location', 'Viana do Castelo');
    });

    it('derives the year from the start date', function () {
        expect(eventsCreate(startsOn: '2023-05-01')['year'])->toBe('2023');
    });

    it('leaves the optional fields null', function () {
        $made = eventsCreate();

        expect($made['ends_on'])->toBeNull()->and($made['url'])->toBeNull();
    });

    it('lists the most recent first', function () {
        eventsCreate('Antiga', '2021-06-01');
        eventsCreate('Recente', '2025-06-01');
        eventsCreate('Intermédia', '2023-06-01');

        expect($this->getJson('/api/events/')->json('events.*.name'))->toBe(['Recente', 'Intermédia', 'Antiga']);
    });

    it('searches by name or location', function () {
        eventsCreate('Feira do Livro', '2025-01-01', ['location' => 'Porto']);
        eventsCreate('Mercado de Natal', '2025-12-01', ['location' => 'Braga']);

        expect($this->getJson('/api/events/?q=Livro')->json('events.*.name'))->toBe(['Feira do Livro'])
            ->and($this->getJson('/api/events/?q=Braga')->json('events.*.name'))->toBe(['Mercado de Natal']);
    });

    it('updates the event', function () {
        $made = eventsCreate('Nome antigo', '2025-01-01');

        $this->putJson("/api/events/{$made['id']}", ['name' => 'Nome novo', 'starts_on' => '2025-01-01'])
            ->assertOk()->assertJsonPath('name', 'Nome novo');
    });

    it('deletes it', function () {
        $made = eventsCreate();

        $this->deleteJson("/api/events/{$made['id']}")->assertOk();
        $this->getJson("/api/events/{$made['id']}")->assertNotFound();
    });

    it('answers 404 for an unknown id', function () {
        $this->getJson('/api/events/9999')->assertNotFound();
    });

    it('refuses missing required fields with 400', function () {
        $this->postJson('/api/events/', ['name' => 'Sem data'])->assertStatus(400);
        $this->postJson('/api/events/', ['starts_on' => '2025-01-01'])->assertStatus(400);
    });
});

describe('guards', function () {
    it('keeps reads public', function () {
        Auth::forgetGuards();

        $this->getJson('/api/events/')->assertOk();
    });

    it('requires a token to write', function () {
        Auth::forgetGuards();

        $this->postJson('/api/events/', ['name' => 'X', 'starts_on' => '2025-01-01'])->assertUnauthorized();
    });

    it('requires a token to delete', function () {
        $made = eventsCreate();
        Auth::forgetGuards();

        $this->deleteJson("/api/events/{$made['id']}")->assertUnauthorized();
    });
});

describe('the timeline section', function () {
    // An empty rail would look broken, so the section is dropped entirely.
    it('is omitted when there are no events', function () {
        $this->get('/')->assertDontSee('id="events"', false)->assertDontSee('Onde já estivemos', false);
    });

    it('renders the events', function () {
        eventsCreate('Feira de Artesanato', '2025-08-12', ['location' => 'Viana do Castelo']);

        $this->get('/')
            ->assertSee('id="events"', false)
            ->assertSee('Feira de Artesanato', false)
            ->assertSee('Viana do Castelo', false);
    });

    it('sits between the range and the contacts', function () {
        makeProductType('Caixa');
        eventsCreate();
        $html = $this->get('/')->getContent();

        expect(strpos($html, 'O que sai da oficina'))->toBeLessThan(strpos($html, 'id="events"'))
            ->and(strpos($html, 'id="events"'))->toBeLessThan(strpos($html, 'id="contacts"'));
    });

    // A rail of one promises a sequence that is not there.
    it('shows a single event as a card, not a rail', function () {
        eventsCreate('Feira de Artesanato', '2025-08-12');

        $this->get('/')
            ->assertSee('Feira de Artesanato', false)
            ->assertDontSee('id="timeline"', false)
            ->assertDontSee('data-timeline-prev', false);
    });

    it('makes the rail a focusable scroll container', function () {
        eventsTwo();

        $this->get('/')
            ->assertSee('id="timeline"', false)
            ->assertSee('tabindex="0"', false)
            ->assertSee('aria-label=', false);
    });

    it('loads the drag script', function () {
        eventsCreate();

        $this->get('/')->assertSee('js/store/timeline.js', false);
    });

    it('renders the arrow buttons', function () {
        eventsTwo();

        $this->get('/')->assertSee('data-timeline-prev', false)->assertSee('data-timeline-next', false);
    });

    // Text glyphs like &#8249; render differently per platform font.
    it('draws the arrows with Font Awesome chevrons', function () {
        eventsTwo();

        $this->get('/')->assertSee('fa-chevron-left', false)->assertSee('fa-chevron-right', false);
    });

    // A full-bleed wrapper once pushed the rail 72px off its header.
    it('aligns the rail with its header', function () {
        eventsTwo();

        $this->get('/')->assertDontSee('timeline-viewport', false)->assertSee('timeline-shell', false);
    });

    it('renders the event link when there is one', function () {
        eventsCreate(fields: ['url' => 'https://example.com/feira']);

        $this->get('/')->assertSee('https://example.com/feira', false);
    });
});

describe('eventDates', function () {
    it('spells a date range in Portuguese', function (array $args, string $expected) {
        expect(Format::eventDates(...$args))->toBe($expected);
    })->with([
        'a single day' => [['2025-08-12'], '12 de Agosto de 2025'],
        'a range within one month collapses' => [['2025-08-12', '2025-08-20'], '12 - 20 de Agosto de 2025'],
        'a range across months keeps both' => [['2025-07-28', '2025-08-03'], '28 de Julho - 3 de Agosto de 2025'],
        'a range across years keeps both years' => [['2024-12-28', '2025-01-03'], '28 de Dezembro de 2024 - 3 de Janeiro de 2025'],
        'the same start and end reads as one day' => [['2025-08-12', '2025-08-12'], '12 de Agosto de 2025'],
        // A bad date must not break the whole landing page.
        'an unparseable value falls back to the raw string' => [['not-a-date'], 'not-a-date'],
        'null is empty' => [[null], ''],
    ]);
});
