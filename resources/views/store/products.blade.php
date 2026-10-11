@extends('layouts.store')

@section('page_title', 'Peças')

@section('content')
<section class="section">
    <div class="container">
        <header class="d-flex flex-wrap align-items-end justify-content-between gap-3 mb-4">
            <div>
                <p class="eyebrow">Catálogo</p>
                <h1 class="display-6 mb-2">Tudo o que fazemos</h1>
                <p class="text-body-secondary mb-0">
                    Peças feitas à mão por encomenda. Preços sob consulta: fale connosco e dizemos-lhe tudo.
                </p>
            </div>

            <div class="d-flex flex-wrap align-items-center gap-2">
                <div id="active-filters" class="d-flex flex-wrap gap-1" hidden></div>
                <span id="result-count" class="fs-7 font-monospace text-body-secondary"></span>
                <button class="btn btn-light d-lg-none" type="button"
                        data-bs-toggle="offcanvas" data-bs-target="#catalogue-filters"
                        aria-controls="catalogue-filters">
                    <span class="icon"><i class="fa-solid fa-sliders"></i></span>
                    <span>Filtros</span>
                </button>
            </div>
        </header>

        <div class="row g-4 g-lg-5">

            <aside class="col-lg-3 filters">
                <div class="offcanvas-lg offcanvas-start" id="catalogue-filters" tabindex="-1"
                     aria-labelledby="catalogue-filters-title">
                    <div class="offcanvas-header border-bottom">
                        <h2 class="offcanvas-title fs-6" id="catalogue-filters-title">Filtros</h2>
                        <button class="btn-close" type="button" data-bs-dismiss="offcanvas"
                                data-bs-target="#catalogue-filters" aria-label="Fechar"></button>
                    </div>

                    <div class="offcanvas-body flex-column d-lg-block">
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2 mb-3">
                            <h2 class="fs-7 fw-semibold text-body-secondary mb-0 d-none d-lg-block">Filtros</h2>
                            <button id="clear-filters" class="btn btn-sm btn-link p-0 fs-7 ms-auto" type="button" hidden>
                                Limpar tudo
                            </button>
                        </div>

                        <div class="mb-4">
                            <label class="visually-hidden" for="filter-search">Pesquisar</label>
                            <input id="filter-search"
                                   class="form-control form-control-sm border-0 border-bottom rounded-0 px-0 bg-transparent"
                                   type="search" placeholder="Procurar uma peça" autocomplete="off">
                        </div>

                        <nav id="filter-groups">
                            <p class="filter-group-label">Tipo</p>
                            <ul class="nav flex-column" data-filter-group="type_id" data-endpoint="/api/product-types/" data-collection-key="product_types" data-facet="types"></ul>

                            <p class="filter-group-label">Material</p>
                            <ul class="nav flex-column" data-filter-group="material_id" data-endpoint="/api/materials/" data-collection-key="materials" data-facet="materials"></ul>
                        </nav>
                    </div>
                </div>
            </aside>

            <section class="col-lg-9 catalogue-main">
                <nav id="grid-crumbs" class="mb-3" aria-label="Onde está" hidden>
                    <ol class="breadcrumb fs-7 mb-0">
                        <li class="breadcrumb-item">
                            <a href="{{ route('store.products', absolute: false) }}" data-crumb-collections>
                                <i class="fa-solid fa-chevron-left fa-xs me-1" aria-hidden="true"></i>Colecções
                            </a>
                        </li>
                        <li class="breadcrumb-item active" aria-current="page" data-crumb-here></li>
                    </ol>
                </nav>

                <div id="collection-grid" class="row row-cols-2 row-cols-lg-3 g-4" hidden></div>

                <div id="product-grid" class="row row-cols-2 row-cols-lg-3 g-4"></div>

                <div id="grid-empty" class="alert alert-light text-center" hidden>
                    Nenhuma peça corresponde aos filtros escolhidos.
                </div>

                <nav id="pagination" class="mt-4 d-flex justify-content-center" aria-label="Paginação" hidden>
                    <ul class="pagination mb-0" id="page-list"></ul>
                </nav>
            </section>
        </div>
    </div>
</section>
@endsection

@section('page_scripts')
<script type="module" src="/static/js/store/products.js"></script>
@endsection
