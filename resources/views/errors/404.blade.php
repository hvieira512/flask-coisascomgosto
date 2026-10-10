@extends('layouts.store')

@section('page_title', 'Página não encontrada')

@section('content')
<section class="section is-medium">
    <div class="container d-flex flex-column align-items-center text-center gap-3">
        @include('components.butterfly', ['class' => 'error-mark'])
        <p class="eyebrow mb-0">Erro 404</p>
        <h1 class="h2 mb-0">Página não encontrada</h1>
        <p class="text-body-secondary measure-narrow mb-2">
            A página que procura não existe ou foi movida. As peças continuam todas no catálogo.
        </p>

        <div class="d-flex flex-wrap justify-content-center gap-2">
            <a class="btn btn-dark" href="{{ route('store.products', absolute: false) }}">Ver as peças</a>
            <a class="btn btn-light" href="{{ route('store.home', absolute: false) }}">Voltar ao início</a>
        </div>
    </div>
</section>
@endsection
