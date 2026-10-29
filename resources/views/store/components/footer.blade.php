@php
    $talk = array_filter([
        ['WhatsApp', 'fa-brands fa-whatsapp', $contact->whatsapp, $contact->whatsappUrl(), true],
        ['E-mail', 'fa-solid fa-envelope', $contact->email, $contact->email ? 'mailto:'.$contact->email : null, false],
    ], fn ($way) => $way[3]);
    $follow = array_filter([
        ['Instagram', 'fa-brands fa-instagram', \App\Support\Format::socialHandle($contact->instagram_url), $contact->instagram_url, true],
        ['Facebook', 'fa-brands fa-facebook-f', \App\Support\Format::socialHandle($contact->facebook_url), $contact->facebook_url, true],
    ], fn ($way) => $way[3]);
@endphp

<footer class="bg-body text-body" id="contacts" data-bs-theme="dark">
    <div class="container pt-5 pb-3">
        <div class="row gy-4 gx-lg-5 pb-5">
            <div class="col-lg-5">
                <p class="font-display fs-3 fw-semibold lh-sm mb-0">Coisas com Gosto</p>
                <p class="fs-7 text-body-secondary mb-0">Viana do Castelo · feito à mão</p>
                @if ($contact->address)
                <p class="font-display fs-5 lh-sm mt-4 mb-2">{{ $contact->address }}</p>
                @endif
                @if ($contact->maps_url)
                <a class="fs-7 fw-semibold border-bottom" href="{{ $contact->maps_url }}"
                   target="_blank" rel="noopener">Ver no mapa<i class="fa-solid fa-arrow-up-right-from-square fa-2xs ms-1" aria-hidden="true"></i></a>
                @endif
            </div>

            @foreach (['Fale connosco' => $talk, 'Siga-nos' => $follow] as $heading => $ways)
            @if ($ways)
            <div class="col-12 col-sm-6 {{ $loop->last ? 'col-lg-4' : 'col-lg-3' }}">
                <p class="eyebrow">{{ $heading }}</p>
                <ul class="list-unstyled d-flex flex-column gap-3 mb-0">
                    @foreach ($ways as [$label, $icon, $value, $href, $external])
                    <li>
                        <a class="d-inline-flex align-items-center gap-2 text-body" href="{{ $href }}"@if ($external) target="_blank" rel="noopener"@endif>
                            <i class="{{ $icon }} fa-fw text-body-secondary" aria-hidden="true"></i>
                            <span class="visually-hidden">{{ $label }}:</span>
                            {{ $value }}
                        </a>
                    </li>
                    @endforeach
                </ul>
            </div>
            @endif
            @endforeach
        </div>

        <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 border-top pt-3 fs-7 text-body-secondary">
            <p class="mb-0">© {{ date('Y') }} Coisas com Gosto</p>

            <nav class="d-flex flex-wrap gap-3" aria-label="rodapé">
                <a class="text-body-secondary"
                   href="{{ route('store.home', absolute: false) }}">Início</a>
                <a class="text-body-secondary"
                   href="{{ route('store.products', absolute: false) }}">Peças</a>
                <a class="text-body-tertiary"
                   href="{{ auth()->check() ? route('dashboard.home', absolute: false) : route('login', absolute: false) }}">Área reservada</a>
            </nav>
        </div>
    </div>
</footer>
