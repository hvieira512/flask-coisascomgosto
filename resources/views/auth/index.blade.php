@extends('layouts.base')

@section('title', 'Entrar · Coisas com Gosto')

@section('styles')
<link rel="stylesheet" href="/static/css/auth.css">
@endsection

@section('body')
<main class="auth-shell">
    <div class="auth-wrapper row g-4">

        <div class="auth-panel col-12 col-md-5 col-lg-4" id="auth-container">
            <a href="{{ route('login', absolute: false) }}" class="auth-logo">
                <img src="/static/img/logo.png" alt="Coisas com Gosto">
            </a>

            <form id="auth-form" class="auth-form">
                <div id="form-header" class="text-center mb-4">
                    <h1 class="h4 mb-1">Seja bem-vindo!</h1>
                    <p class="text-body-secondary">Qual é o teu nome?</p>
                </div>

                <div class="mb-3">
                    <div class="input-group input-group-lg">
                        <input type="text" class="form-control form-control-lg" placeholder="Utilizador"
                                                                                name="username" id="usernameField" aria-label="Utilizador" required autofocus>
                        <span class="input-group-text"><i class="fa-solid fa-user" aria-hidden="true"></i></span>
                    </div>
                    <p id="usernameErrorField" class="help text-danger mb-0"></p>
                </div>

                <div class="d-flex justify-content-end mt-4">
                    <button type="submit" id="submitBtn" class="btn btn-dark">
                        <span>Entrar</span>
                        <span class="icon"><i class="fa-solid fa-arrow-right"></i></span>
                    </button>
                </div>
            </form>

            <a class="fs-7 fw-semibold" role="button">
                Esqueceu-se da sua palavra-passe?
            </a>
        </div>

        <aside class="auth-aside col d-none d-md-block">
            <div class="auth-glass">
                <p class="text-uppercase fs-7">Coisas com Gosto</p>
                <div class="text-end">
                    <h2 class="h1 text-white">
                        Tradição em Madeira<br>Inspirada na Filigrana<br>Portuguesa
                    </h2>
                    <p class="mt-3">
                    Descubra peças únicas que celebram a arte e a cultura de
                    Viana do Castelo, feitas com dedicação e paixão.
                    </p>
                </div>
            </div>
        </aside>
    </div>
</main>
@endsection

@section('scripts')
<script src="/static/sweetalert2/sweetalert2.all.min.js"></script>
<script type="module" src="/static/js/auth/auth.js"></script>
@endsection
