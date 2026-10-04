<nav class="navbar navbar-expand-lg bg-body border-bottom py-3" aria-label="main navigation">
    <div class="container">
        <a class="navbar-brand d-flex align-items-center gap-2 me-0"
           href="{{ route('store.home', absolute: false) }}">
            <img src="/static/img/logo.png"
                 alt="" width="30" height="30">
            <span class="font-display fs-5 fw-semibold text-body">Coisas com Gosto</span>
        </a>

        <button class="navbar-toggler border-0 shadow-none" type="button"
                data-bs-toggle="collapse" data-bs-target="#store-nav"
                aria-controls="store-nav" aria-expanded="false" aria-label="Abrir menu">
            <span class="navbar-toggler-icon"></span>
        </button>

        <div id="store-nav" class="collapse navbar-collapse">
            <ul class="navbar-nav nav-underline ms-auto align-items-lg-center gap-lg-2">
                <li class="nav-item">
                    <a class="nav-link text-uppercase fs-7"
                       href="{{ route('store.home', absolute: false) }}"
                       @if (request()->routeIs('store.home')) aria-current="page" @endif>Início</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link text-uppercase fs-7"
                       href="{{ route('store.products', absolute: false) }}"
                       @if (request()->routeIs('store.products', 'store.product')) aria-current="page" @endif>Produtos</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link text-uppercase fs-7"
                       href="{{ route('store.home', absolute: false) }}#contacts">Contactos</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link text-uppercase fs-7 text-body-tertiary"
                       href="{{ auth()->check() ? route('dashboard.home', absolute: false) : route('login', absolute: false) }}">
                        Área reservada
                    </a>
                </li>
            </ul>
        </div>
    </div>
</nav>
