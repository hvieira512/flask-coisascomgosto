@extends('layouts.store')

@section('page_title', 'Erro do servidor')

@section('content')
<section class="section is-medium">
    <div class="container d-flex flex-column align-items-center text-center gap-3">
        @include('components.butterfly', ['class' => 'error-mark'])
        <p class="eyebrow mb-0">Erro 500</p>
        <h1 class="h2 mb-0">Algo correu mal</h1>
        <p class="text-body-secondary measure-narrow mb-2">
            Ocorreu um erro inesperado do nosso lado. Tente novamente dentro de momentos.
        </p>

        <div class="d-flex justify-content-center">
            <a class="btn btn-dark" href="{{ route('store.home', absolute: false) }}">Voltar ao início</a>
        </div>
    </div>
</section>
@endsection
