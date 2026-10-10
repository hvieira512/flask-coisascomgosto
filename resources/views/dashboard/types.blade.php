@extends('layouts.dashboard')

@section('page_title', 'Tipos')

@section('content')
@include('dashboard.components.page-head', ['eyebrow' => 'Catálogo', 'title' => 'Tipos e materiais',
    'countId' => 'type-count', 'buttonId' => 'new-type', 'buttonLabel' => 'Novo tipo'])

<div class="row g-4">
    <div class="col-lg-8">
        <div>
            <div class="dash-table-wrap">
                <table class="table dash-table table-hover">
                    <thead>
                        <tr>
                            <th class="dash-col-thumb"><span class="visually-hidden">Foto</span></th>
                            <th class="dash-col-name">Tipo</th>
                            <th>Sem fotografia mostra</th>
                            <th class="dash-col-photos">Peças</th>
                            <th class="dash-col-actions"><span class="visually-hidden">Acções</span></th>
                        </tr>
                    </thead>
                    <tbody id="type-rows"></tbody>
                </table>
            </div>
        </div>

        <p class="help mt-2 mb-0">A fotografia é emprestada de uma peça do tipo — é a
            mesma que a loja mostra. O desenho é o que aparece no lugar da fotografia
            enquanto a peça não tiver nenhuma. Um tipo com peças não se apaga: mude-as
            de tipo primeiro.</p>
    </div>

    <div class="col-lg-4">
        <div class="card dash-panel p-4 h-100">
            <header class="d-flex justify-content-between align-items-baseline mb-3">
                <h2 class="h6 mb-0">Materiais</h2>
                <span class="data text-body-secondary" id="material-count">—</span>
            </header>

            <div id="material-rows" class="mb-3"></div>

            <form id="material-form" class="input-group input-group-sm">
                <input class="form-control" id="material-name" required
                       placeholder="Pasta de modelar" aria-label="Nome do material">
                <button class="btn btn-outline-secondary" type="submit">Adicionar</button>
            </form>
            <p class="help mt-2 mb-0" id="material-note">De que são feitas as peças.
                Uma peça pode ser feita de mais do que um material, por isso a soma
                pode passar do número de peças.</p>
        </div>
    </div>
</div>

@include('dashboard.components.modal', ['id' => 'newTypeModal', 'title' => 'Novo tipo'])
@include('dashboard.components.modal', ['id' => 'editTypeModal', 'title' => 'Editar tipo'])
@include('dashboard.components.modal', ['id' => 'deleteTypeModal', 'title' => 'Apagar tipo'])
@endsection

@section('page_scripts')
<script type="module" src="/static/js/dashboard/types/main.js"></script>
@endsection
