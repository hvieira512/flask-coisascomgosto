@extends('layouts.store')

@section('page_title', 'Página não encontrada')

@section('content')
<section class="section is-medium">
    <div class="container text-center">
        <p class="eyebrow">Erro 404</p>
        <h1 class="h2 mb-3">Página não encontrada</h1>
        <p class="text-body-secondary">
            A página que procura não existe ou foi movida.
        </p>

        <div class="d-flex flex-wrap justify-content-center gap-2 mt-5">
            <a class="btn btn-dark" href="{{ route('store.home', absolute: false) }}">Voltar ao início</a>
            <a class="btn btn-light" href="{{ route('store.products', absolute: false) }}">Ver catálogo</a>
        </div>
    </div>
</section>
@endsection
