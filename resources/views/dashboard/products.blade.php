@extends('layouts.dashboard')

@section('page_title', 'Peças')

@section('content')
@include('dashboard.components.page-head', ['eyebrow' => 'Catálogo', 'title' => 'Peças',
    'countId' => 'product-count', 'buttonId' => 'new-product', 'buttonLabel' => 'Nova peça'])

<div class="row row-cols-2 row-cols-lg-5 g-2 align-items-end mb-4" role="search">
    @include('dashboard.components.filter-field', ['id' => 'filter-q', 'label' => 'Pesquisar',
        'placeholder' => 'Nome da peça'])
    @include('dashboard.components.filter-field', ['id' => 'filter-type', 'label' => 'Tipo',
        'options' => [['', 'Todos']]])
    @include('dashboard.components.filter-field', ['id' => 'filter-collection', 'label' => 'Colecção',
        'options' => [['', 'Todas']]])
    @include('dashboard.components.filter-field', ['id' => 'filter-photos', 'label' => 'Fotografias',
        'options' => [['', 'Todas'], ['none', 'Sem fotografia'], ['some', 'Com fotografia']]])

    <div class="col d-flex align-items-end">
        <button class="btn btn-sm btn-ghost" id="filter-clear" hidden>
            <span class="icon"><i class="fa-solid fa-xmark"></i></span>
            <span>Limpar</span>
        </button>
    </div>
</div>

<div>
    <div class="dash-table-wrap">
        <table class="table dash-table is-wide table-hover">
            <thead>
                <tr>
                    <th class="dash-col-thumb"><span class="visually-hidden">Fotografia</span></th>
                    <th class="dash-col-name">Peça</th>
                    <th>Cores</th>
                    <th class="dash-col-photos">Fotografias</th>
                    <th class="dash-col-actions"><span class="visually-hidden">Acções</span></th>
                </tr>
            </thead>
            <tbody id="product-list"></tbody>
        </table>
    </div>

    {{-- d-flex on the inner element: on the nav itself it outranks [hidden]. --}}
    <nav id="product-pager" class="mt-3" aria-label="Páginas" hidden>
        <div class="d-flex align-items-center justify-content-end gap-2">
            <button class="btn btn-sm btn-ghost" id="pager-prev" type="button" aria-label="Página anterior">
                <span class="icon"><i class="fa-solid fa-chevron-left"></i></span>
            </button>
            <span class="fs-7 text-body-secondary data" id="pager-label"></span>
            <button class="btn btn-sm btn-ghost" id="pager-next" type="button" aria-label="Página seguinte">
                <span class="icon"><i class="fa-solid fa-chevron-right"></i></span>
            </button>
        </div>
    </nav>
</div>

@include('dashboard.components.modal', ['id' => 'newProductModal', 'title' => 'Nova peça'])
@include('dashboard.components.modal', ['id' => 'editProductModal', 'title' => 'Editar peça'])
@include('dashboard.components.modal', ['id' => 'deleteProductModal', 'title' => 'Apagar peça'])
@endsection

@section('page_scripts')
<script type="module" src="/static/js/dashboard/products/main.js"></script>
@endsection
