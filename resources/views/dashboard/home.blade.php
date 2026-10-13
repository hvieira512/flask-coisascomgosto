@extends('layouts.dashboard')

@section('page_title', 'Início')

@section('content')
<header class="d-flex flex-wrap align-items-end justify-content-between gap-4 pb-3 mb-4 border-bottom">
    <div>
        <p class="eyebrow">Painel</p>
        <h1 class="font-display dash-title mb-0">Olá, {{ auth()->user()->username }}</h1>
        <p class="text-body-secondary mt-2 mb-0">O que os visitantes andam a ver.</p>
    </div>

    <div class="btn-group btn-group-sm" role="group" aria-label="Período">
        <button class="btn btn-outline-secondary" data-days="7" aria-pressed="false">7 dias</button>
        <button class="btn btn-outline-secondary" data-days="30" aria-pressed="false">30 dias</button>
        <button class="btn btn-outline-secondary" data-days="90" aria-pressed="false">90 dias</button>
    </div>
</header>

<p class="text-body-secondary fs-7 mb-4" id="catalogue-line">—</p>

<section id="totals" class="mb-4"></section>

<div class="row g-4">
    <div class="col-lg-7">
        <div class="card dash-panel p-4">
            <header class="d-flex justify-content-between align-items-baseline mb-3">
                <h2 class="h6 mb-0">Peças mais abertas</h2>
                <span class="fs-7 text-body-secondary">aberturas · pedidos</span>
            </header>
            <div id="most-viewed"></div>
        </div>
    </div>

    <div class="col-lg-5 d-flex flex-column gap-4">
        <div class="card dash-panel p-4">
            <header class="mb-3">
                <h2 class="h6 mb-0">O que perguntam</h2>
                <p class="help mb-0">As cores em que pedem as peças.</p>
            </header>
            <div id="asked-colors"></div>
        </div>

        <div class="card dash-panel p-4">
            <header class="mb-3">
                <h2 class="h6 mb-0">Filtros mais usados</h2>
            </header>
            <div id="top-filters"></div>
        </div>
    </div>
</div>
@endsection

@section('page_scripts')
<script type="module" src="/static/js/dashboard/home.js"></script>
@endsection
