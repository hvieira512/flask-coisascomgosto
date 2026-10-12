<section class="section pb-5 bg-body-secondary" id="events">
    <div class="container">
        <header class="mb-4">
            <p class="eyebrow">Percurso</p>
            <h2 class="h2 mb-3">Onde já estivemos</h2>
            <p class="text-body-secondary measure">
                Feiras, mercados e mostras onde levámos as nossas peças.
            </p>
        </header>

        @if (count($events) === 1)
        <div class="card p-4 measure">
            <div class="timeline-body">@include('store.components.event', ['event' => $events[0]])</div>
        </div>
        @else
        <div class="timeline-shell">
            <button class="disc rail-arrow rail-arrow-start" type="button"
                    data-timeline-prev aria-label="Eventos anteriores" hidden>
                <span class="icon"><i class="fa-solid fa-chevron-left"></i></span>
            </button>

            <ol class="drag-rail timeline" id="timeline" tabindex="0"
                aria-label="Cronologia de eventos, arraste para o lado">
                @foreach ($events as $event)
                <li class="timeline-entry">
                    <div class="timeline-marker" aria-hidden="true"></div>

                    <div class="timeline-body">@include('store.components.event', ['event' => $event])</div>
                </li>
                @endforeach
            </ol>

            <button class="disc rail-arrow rail-arrow-end" type="button"
                    data-timeline-next aria-label="Eventos seguintes" hidden>
                <span class="icon"><i class="fa-solid fa-chevron-right"></i></span>
            </button>
        </div>
        @endif
    </div>
</section>
