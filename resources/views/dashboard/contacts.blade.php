@extends('layouts.dashboard')

@section('page_title', 'Contactos')

@section('content')
@include('dashboard.components.page-head', ['eyebrow' => 'Oficina', 'title' => 'Contactos',
    'subtitle' => 'O que aparece no fim da página inicial e no rodapé da loja.'])

<div class="row g-4">
    <div class="col-lg-7">
        <form class="card dash-panel p-4 h-100" id="contact-form">
            <h2 class="h6 mb-3">Onde nos encontram</h2>

            <div class="mb-3">
                <label class="form-label" for="cf-address">Morada</label>
                <input class="form-control" id="cf-address" name="address"
                       placeholder="Rua de Cardielos, n. 222, Viana do Castelo">
            </div>

            <div class="mb-3">
                <label class="form-label" for="cf-maps_url">Ligação do mapa</label>
                <input class="form-control" id="cf-maps_url" name="maps_url"
                       placeholder="https://maps.app.goo.gl/...">
                <p class="help mb-0">Onde abre a morada. Prefira a ligação curta do Google Maps.</p>
            </div>

            <div class="mb-3">
                <label class="form-label" for="cf-email">E-mail</label>
                <input class="form-control" id="cf-email" name="email" type="email"
                       placeholder="geral@coisascomgosto.pt">
            </div>

            <h2 class="h6 mt-4 mb-3">Redes</h2>

            <div class="mb-3">
                <label class="form-label" for="cf-whatsapp">WhatsApp</label>
                <input class="form-control" id="cf-whatsapp" name="whatsapp" inputmode="numeric"
                       placeholder="939320334">
                <p class="help mb-0" id="cf-whatsapp-preview"></p>
            </div>

            <div class="mb-3">
                <label class="form-label" for="cf-facebook_url">Facebook</label>
                <input class="form-control" id="cf-facebook_url" name="facebook_url"
                       placeholder="https://www.facebook.com/...">
            </div>

            <div class="mb-3">
                <label class="form-label" for="cf-instagram_url">Instagram</label>
                <input class="form-control" id="cf-instagram_url" name="instagram_url"
                       placeholder="https://www.instagram.com/...">
            </div>

            <div class="d-flex gap-2 mt-4">
                <button class="btn btn-dark" id="contact-save" type="submit">Guardar</button>
                <button class="btn btn-ghost" id="contact-reset" type="button">Repor</button>
            </div>
        </form>
    </div>

    <div class="col-lg-5">
        <div class="card dash-panel p-4 h-100">
            <h2 class="h6 mb-3">Como aparece na loja</h2>
            <div id="contact-preview"></div>
            <p class="help mt-3 mb-0">Uma linha só aparece quando o campo está preenchido.</p>
        </div>
    </div>
</div>
@endsection

@section('page_scripts')
<script type="module" src="/static/js/dashboard/contacts.js"></script>
@endsection
