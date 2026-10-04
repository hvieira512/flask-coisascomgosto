@extends('layouts.store')

@section('page_title', 'Erro do servidor')

@section('content')
<section class="section is-medium">
    <div class="container text-center">
        <p class="eyebrow">Erro 500</p>
        <h1 class="h2 mb-3">Algo correu mal</h1>
        <p class="text-body-secondary">
            Ocorreu um erro inesperado. Tente novamente dentro de momentos.
        </p>

        <div class="d-flex justify-content-center mt-5">
            <a class="btn btn-dark" href="{{ route('store.home', absolute: false) }}">Voltar ao início</a>
        </div>
    </div>
</section>
@endsection
