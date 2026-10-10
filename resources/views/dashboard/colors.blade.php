@extends('layouts.dashboard')

@section('page_title', 'Cores')

@section('content')
@include('dashboard.components.page-head', ['eyebrow' => 'Catálogo', 'title' => 'Cores e conjuntos',
    'countId' => 'set-count', 'buttonId' => 'new-set', 'buttonLabel' => 'Novo conjunto'])

<div class="row g-4">
    <div class="col-lg-8">
        <div class="row row-cols-2 row-cols-lg-4 g-2 align-items-end mb-3" role="search">
            @include('dashboard.components.filter-field', ['id' => 'set-filter-q', 'label' => 'Pesquisar',
                'placeholder' => 'Nome do conjunto'])
            @include('dashboard.components.filter-field', ['id' => 'set-filter-collection', 'label' => 'Colecção',
                'options' => [['', 'Todas']]])
            @include('dashboard.components.filter-field', ['id' => 'set-filter-pieces', 'label' => 'Peças',
                'options' => [['', 'Todos'], ['none', 'Sem peças'], ['some', 'Com peças']]])

            <div class="col d-flex align-items-end">
                <button class="btn btn-sm btn-ghost" id="set-filter-clear" hidden>
                    <span class="icon"><i class="fa-solid fa-xmark"></i></span>
                    <span>Limpar</span>
                </button>
            </div>
        </div>

        <div>
            <div class="dash-table-wrap">
                <table class="table dash-table table-hover">
                    <thead>
                        <tr>
                            <th class="dash-col-name">Conjunto</th>
                            <th>Cores</th>
                            <th>Colecção</th>
                            <th class="dash-col-photos">Peças</th>
                            <th class="dash-col-actions"><span class="visually-hidden">Acções</span></th>
                        </tr>
                    </thead>
                    <tbody id="set-rows"></tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="col-lg-4">
        <div class="card dash-panel p-4 h-100">
            <header class="d-flex justify-content-between align-items-baseline mb-3">
                <h2 class="h6 mb-0">Cores</h2>
                <span class="data text-body-secondary" id="color-count">—</span>
            </header>

            <div id="color-rows" class="mb-3"></div>

            <form id="color-form" class="mb-0">
                <div class="input-group input-group-sm">
                    <input class="form-control form-control-color color-swatch-input"
                           type="color" id="color-hex" value="#4472C4" aria-label="Cor">
                    <input class="form-control" id="color-name" required
                           placeholder="Dourado" aria-label="Nome da cor">
                    <button class="btn btn-outline-secondary" type="submit">Adicionar</button>
                </div>
            </form>
            <p class="help mt-2 mb-0">Cada cor pode entrar em vários conjuntos.</p>
        </div>
    </div>
</div>

@include('dashboard.components.modal', ['id' => 'newSetModal', 'title' => 'Novo conjunto'])
@include('dashboard.components.modal', ['id' => 'editSetModal', 'title' => 'Editar conjunto'])
@include('dashboard.components.modal', ['id' => 'deleteSetModal', 'title' => 'Apagar conjunto'])
@include('dashboard.components.modal', ['id' => 'editColorModal', 'title' => 'Editar cor'])
@include('dashboard.components.modal', ['id' => 'deleteColorModal', 'title' => 'Apagar cor'])
@endsection

@section('page_scripts')
<script type="module" src="/static/js/dashboard/colors/main.js"></script>
@endsection
