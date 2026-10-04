@php
    $catalogue = [
        ['Peças', 'dashboard.products', $counts->pieces],
        ['Tipos', 'dashboard.types', null],
        ['Cores', 'dashboard.colors', $counts->color_sets],
        ['Colecções', 'dashboard.collections', $counts->collections],
    ];
    $workshop = [
        ['Feiras', 'dashboard.events', $counts->events],
        ['Contactos', 'dashboard.contacts', null],
    ];
@endphp

<aside class="offcanvas-lg offcanvas-start dash-sidebar" id="sidebar" tabindex="-1"
       aria-label="Secções do painel">
    <div class="offcanvas-header">
        <span class="offcanvas-title font-display">Secções</span>
        <button class="btn-close" data-bs-dismiss="offcanvas" data-bs-target="#sidebar"
                aria-label="Fechar"></button>
    </div>

    <div class="offcanvas-body d-flex flex-column py-4 px-0">
        <a class="dash-brand font-display fs-6 px-4 pb-3 text-decoration-none"
           href="{{ route('dashboard.home', absolute: false) }}">Coisas com Gosto<span>.</span></a>

        <div class="px-2">
            <p class="eyebrow px-2 mb-2">O que acontece</p>
            @include('dashboard.components.rail-link', ['label' => 'Início', 'route' => 'dashboard.home', 'count' => null])
        </div>

        @foreach (['Catálogo' => $catalogue, 'A oficina' => $workshop] as $head => $sections)
        <div class="px-2 mt-4">
            <p class="eyebrow px-2 mb-2">{{ $head }}</p>
            @foreach ($sections as [$label, $route, $count])
            @include('dashboard.components.rail-link', compact('label', 'route', 'count'))
            @endforeach
        </div>
        @endforeach

        <div class="mt-auto px-2 pt-4">
            @include('dashboard.components.rail-link', ['label' => '← Ver a loja', 'route' => 'store.home', 'count' => null])
        </div>
    </div>
</aside>
