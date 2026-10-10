@php
    $reach = [
        ['WhatsApp', $contact->whatsapp, $contact->whatsappUrl(), true],
        ['E-mail', $contact->email, $contact->email ? 'mailto:'.$contact->email : null, false],
        ['Instagram', \App\Support\Format::socialHandle($contact->instagram_url), $contact->instagram_url, true],
        ['Facebook', \App\Support\Format::socialHandle($contact->facebook_url), $contact->facebook_url, true],
    ];
@endphp

<section class="section pb-4 bg-body text-body" id="contacts" data-bs-theme="dark">
    <div class="container">
        <p class="eyebrow">Contactos</p>
        <h2 class="h1 mb-4">Onde nos encontra</h2>

        <div class="row g-5">
            <div class="col-lg-5">
                @if ($contact->address)
                <p class="font-display fs-4 lh-sm mb-2">{{ $contact->address }}</p>
                @endif
                @if ($contact->maps_url)
                <a class="fs-7 fw-semibold border-bottom" href="{{ $contact->maps_url }}"
                   target="_blank" rel="noopener">Ver no mapa</a>
                @endif
            </div>

            <div class="col-lg-7">
                <dl class="mb-0">
                    @foreach ($reach as [$label, $value, $href, $external])
                    @if ($href)
                    <div class="row gx-2 align-items-center border-top py-2">
                        <dt class="col-4 col-sm-3 fs-7 fw-semibold text-uppercase text-body-secondary mb-0">{{ $label }}</dt>
                        <dd class="col-8 col-sm-9 mb-0">
                            <a href="{{ $href }}"@if ($external) target="_blank" rel="noopener"@endif>{{ $value }}</a>
                        </dd>
                    </div>
                    @endif
                    @endforeach
                </dl>
            </div>
        </div>
    </div>
</section>
