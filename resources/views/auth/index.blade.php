@extends('layouts.base')

@section('title', 'Entrar · Coisas com Gosto')

@section('styles')
<link rel="stylesheet" href="/static/css/auth.css">
@endsection

@section('body')
<main class="d-flex flex-column flex-md-row min-vh-100">

    <section class="auth-panel d-flex flex-column justify-content-between p-4 p-md-5" id="auth-container">
        <a class="d-inline-flex align-items-center gap-2 text-body align-self-start"
           href="{{ route('store.home', absolute: false) }}">
            <img src="/static/img/logo.png" alt="" width="32" height="32" class="rounded-circle">
            <span class="font-display fs-5 fw-semibold">Coisas com Gosto</span>
        </a>

        <form id="auth-form" class="auth-form w-100 mx-auto py-5">
            <div id="form-header" class="mb-4">
                <p class="eyebrow">Área reservada</p>
                <h1 class="h2 font-display mb-2">Entrar no painel</h1>
                <p class="text-body-secondary mb-0">Primeiro o nome de utilizador, depois a palavra-passe.</p>
            </div>

            <div class="mb-3">
                <label class="form-label" for="usernameField">Utilizador</label>
                <input type="text" class="form-control form-control-lg" name="username" id="usernameField"
                       autocomplete="username" required autofocus>
            </div>

            <div class="d-grid mt-4">
                <button type="submit" id="submitBtn" class="btn btn-dark btn-lg">
                    <span>Continuar</span>
                    <span class="icon"><i class="fa-solid fa-arrow-right"></i></span>
                </button>
            </div>

            <p class="help mt-3 mb-0">
                As contas são criadas pela oficina. Se se esqueceu da palavra-passe, peça
                uma nova a quem gere o painel.
            </p>
        </form>

        <p class="fs-7 mb-0">
            <a href="{{ route('store.home', absolute: false) }}">← Voltar à loja</a>
        </p>
    </section>

    <aside class="auth-aside d-none d-md-block p-3" aria-hidden="true">
        <div class="position-relative h-100 overflow-hidden rounded-4 bg-body-secondary">
            <img class="w-100 h-100 object-fit-cover" src="/static/img/hero-lid.jpg" alt="">
            <span class="position-absolute bottom-0 start-0 m-4 badge rounded-pill bg-body text-body-secondary fw-normal fs-7 px-3 py-2">
                Caixa Redonda Filigrana · Branco e Dourado
            </span>
        </div>
    </aside>

</main>
@endsection

@section('scripts')
<script src="/static/sweetalert2/sweetalert2.all.min.js"></script>
<script type="module" src="/static/js/auth/auth.js"></script>
@endsection
