<footer data-bs-theme="dark" class="bg-body text-body py-4">
    <div class="container d-flex flex-wrap align-items-center justify-content-between gap-3">
        <p class="fs-7 text-body-secondary mb-0">Coisas com Gosto · Viana do Castelo</p>

        <nav class="d-flex flex-wrap gap-3" aria-label="rodapé">
            <a class="fs-7 text-body-secondary text-decoration-none"
               href="{{ route('store.home', absolute: false) }}">Início</a>
            <a class="fs-7 text-body-secondary text-decoration-none"
               href="{{ route('store.products', absolute: false) }}">Peças</a>
            <a class="fs-7 text-body-secondary text-decoration-none"
               href="{{ route('store.home', absolute: false) }}#contacts">Contactos</a>
        </nav>

        <p class="fs-7 text-body-tertiary mb-0">{{ date('Y') }}</p>
    </div>
</footer>
