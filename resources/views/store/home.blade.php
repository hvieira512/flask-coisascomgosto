@extends('layouts.store')

@section('page_title', 'Início')

@section('content')
<header class="hero">
    <div class="container py-5">
        <div class="row align-items-center gy-5 gx-lg-5 py-lg-4">
            <div class="col-lg-6">
                <p class="eyebrow">Viana do Castelo · feito à mão</p>

                <h1 class="store-display mb-4">
                    Peças que guardam<br>a nossa terra.
                </h1>

                <p class="fs-5 text-body-secondary measure-narrow mb-4">
                Madeira e tecido trabalhados um a um, com os motivos que
                atravessam gerações no Alto Minho.
                </p>

                <div class="d-flex flex-wrap gap-2">
                    <a class="btn btn-dark btn-lg" href="{{ route('store.products', absolute: false) }}">
                        <span>Ver as peças</span>
                        <span class="icon"><i class="fa-solid fa-arrow-right"></i></span>
                    </a>
                    <a class="btn btn-light btn-lg" href="#origem">A nossa história</a>
                </div>
            </div>

            <div class="col-lg-6 d-flex flex-column align-items-center py-4">
                <div class="hero-stage position-relative" data-hero-box data-lid="/static/img/hero-lid.jpg">
                    <img class="hero-fallback" src="/static/img/hero-lid.jpg"
                         alt="Caixa redonda em madeira branca, a tampa pintada com a filigrana de Viana a dourado">
                    <i class="fa-solid fa-hand-pointer hero-hand position-absolute" aria-hidden="true"></i>
                </div>
            </div>
        </div>
    </div>
</header>

@if ($productTypes->isNotEmpty())
<section class="section" id="pecas">
    <div class="container">
        <header class="mb-4">
            <p class="eyebrow">As peças</p>
            <h2 class="h1 mb-3">O que sai da oficina</h2>
            <p class="text-body-secondary measure mb-0">
            Escolha uma família de peças para ver tudo o que temos dela.
            </p>
        </header>

        <div class="row row-cols-2 row-cols-md-3 row-cols-lg-4 g-3">
            @foreach ($productTypes as $type)
            @php($cover = $type->getRelation('cover'))
            <div class="col">
                <a class="d-block position-relative overflow-hidden rounded-3 text-decoration-none h-100"
                   href="{{ route('store.products', ['type_id' => $type->id, 'all' => 1], false) }}">
                    <div class="ratio" style="--bs-aspect-ratio: 125%">
                        @if ($cover)
                        <img class="object-fit-cover" src="{{ $cover['url'] }}" alt="{{ $cover['alt'] }}" loading="lazy">
                        @else
                        <span class="d-flex flex-column align-items-center justify-content-center text-center bg-body-secondary border p-3">
                            <span class="font-display fs-4 text-body-secondary">{{ $type->name }}</span>
                            <span class="fs-7 text-body-secondary">fotografia a caminho</span>
                        </span>
                        @endif
                    </div>

                    @if ($cover)
                    <span class="position-absolute top-0 start-0 w-100 h-100 tile-scrim" aria-hidden="true"></span>
                    <span class="position-absolute bottom-0 start-0 p-3 text-white">
                        <span class="d-block font-display fs-5 lh-sm">{{ $type->name }}</span>
                        <span class="fs-7 opacity-75">
                            {{ $type->pieces }} {{ $type->pieces === 1 ? 'peça' : 'peças' }}
                        </span>
                    </span>
                    @endif
                </a>
            </div>
            @endforeach

            <div class="col">
                <a class="d-flex flex-column justify-content-end h-100 p-3 rounded-3 bg-dark text-white text-decoration-none"
                   href="{{ route('store.products', absolute: false) }}">
                    <span class="icon mb-auto text-white-50"><i class="fa-solid fa-arrow-right"></i></span>
                    <span class="d-block font-display fs-5 lh-sm">Ver tudo</span>
                    <span class="fs-7 opacity-75">o catálogo</span>
                </a>
            </div>
        </div>
    </div>
</section>
@endif

<section class="section bg-body-secondary" id="origem">
    <div class="container">
        <div class="row align-items-center g-5">
            <div class="col-lg-7">
                <img class="origin-photo w-100 rounded-4 object-fit-cover" src="/static/img/hero.webp"
                     alt="Os dois artesãos da Coisas com Gosto na banca da feira"
                     style="aspect-ratio: 4 / 3" loading="lazy">
            </div>
            <div class="col-lg-5">
                <p class="eyebrow">Origem</p>
                <h2 class="h1 mb-3">Começou numa bancada pequena</h2>
                <p class="text-body-secondary">
                A Coisas com Gosto nasceu do gosto por trabalhar madeira em
                casa, ao fim do dia, em Viana do Castelo. Primeiro foram
                lembranças para a família. Depois pediram-nos uma, e outra,
                e a bancada deixou de chegar.
                </p>
                <p class="text-body-secondary mb-0">
                Continuamos a fazer tudo aqui, à mão, no mesmo sítio. Nada
                sai da oficina sem passar por nós.
                </p>
            </div>
        </div>
    </div>
</section>

<section class="section" id="oficio">
    <div class="container">
        <header class="mb-5">
            <p class="eyebrow">O ofício</p>
            <h2 class="h1 measure mb-0">Cada peça passa por três mãos-cheias de tempo</h2>
        </header>

        <ol class="row row-cols-1 row-cols-md-3 g-4 list-unstyled mb-0">
            <li class="col border-top pt-3">
                <p class="eyebrow mb-2">Passo 1</p>
                <h3 class="h4">Desenhar</h3>
                <p class="text-body-secondary mb-0">
                Começa tudo no desenho. Pensamos a peça a partir do que
                ela vai servir, e é o uso que decide a forma que vai ter.
                </p>
            </li>
            <li class="col border-top pt-3">
                <p class="eyebrow mb-2">Passo 2</p>
                <h3 class="h4">Pintar</h3>
                <p class="text-body-secondary mb-0">
                As cores são dadas à mão, camada sobre camada, seguindo
                os padrões que herdámos dos trajes da região.
                </p>
            </li>
            <li class="col border-top pt-3">
                <p class="eyebrow mb-2">Passo 3</p>
                <h3 class="h4">Acabar</h3>
                <p class="text-body-secondary mb-0">
                Lixar, selar e montar. É aqui que se decide se leva fio
                para pendurar ou se fica de pé, à espera de companhia.
                </p>
            </li>
        </ol>
    </div>
</section>

@if ($events->isNotEmpty())
@include('store.components.timeline')
@endif

@include('store.components.contacts')

@endsection

@section('page_scripts')
<script type="module" src="/static/js/store/hero-box.js"></script>
@endsection
