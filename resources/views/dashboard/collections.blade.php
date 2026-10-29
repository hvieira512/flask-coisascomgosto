@extends('layouts.dashboard')

@section('page_title', 'Colecções')

@section('content')
@include('dashboard.components.page-head', ['eyebrow' => 'Catálogo', 'title' => 'Colecções',
    'countId' => 'collection-count', 'buttonId' => 'new-collection', 'buttonLabel' => 'Nova colecção'])

<div>
    <div class="dash-table-wrap">
        <table class="table dash-table table-hover">
            <thead>
                <tr>
                    <th class="dash-col-thumb"><span class="visually-hidden">Capa</span></th>
                    <th class="dash-col-name">Colecção</th>
                    <th>Descrição</th>
                    <th class="dash-col-photos">Peças</th>
                    <th class="dash-col-actions"><span class="visually-hidden">Acções</span></th>
                </tr>
            </thead>
            <tbody id="collection-rows"></tbody>
        </table>
    </div>
</div>

<p class="help mt-3">
    A capa é a fotografia que representa a colecção no catálogo. Sem capa, a
    colecção aparece com o mesmo lugar reservado das peças sem fotografia.
</p>

@include('dashboard.components.modal', ['id' => 'newCollectionModal', 'title' => 'Nova colecção'])
@include('dashboard.components.modal', ['id' => 'editCollectionModal', 'title' => 'Editar colecção'])
@include('dashboard.components.modal', ['id' => 'deleteCollectionModal', 'title' => 'Apagar colecção'])
@endsection

@section('page_scripts')
<script type="module" src="/static/js/dashboard/collections/main.js"></script>
@endsection
