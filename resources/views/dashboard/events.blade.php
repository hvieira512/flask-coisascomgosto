@extends('layouts.dashboard')

@section('page_title', 'Feiras')

@section('content')
@include('dashboard.components.page-head', ['eyebrow' => 'Oficina', 'title' => 'Feiras',
    'countId' => 'event-count', 'buttonId' => 'new-event', 'buttonLabel' => 'Nova feira'])

<div>
    <div class="dash-table-wrap">
        <table class="table dash-table is-wide table-hover" id="event-table">
            <thead>
                <tr>
                    <th class="dash-col-name">Feira</th>
                    <th>Local</th>
                    <th>Datas</th>
                    <th class="dash-col-actions"><span class="visually-hidden">Acções</span></th>
                </tr>
            </thead>
            <tbody id="event-rows"></tbody>
        </table>
    </div>
</div>

<p class="help mt-3 mb-0">O que aparece em «Onde já estivemos», na página inicial da loja.</p>

@include('dashboard.components.modal', ['id' => 'newEventModal', 'title' => 'Nova feira'])
@include('dashboard.components.modal', ['id' => 'editEventModal', 'title' => 'Editar feira'])
@include('dashboard.components.modal', ['id' => 'deleteEventModal', 'title' => 'Apagar feira'])
@endsection

@section('page_scripts')
<script type="module" src="/static/js/dashboard/events/main.js"></script>
@endsection
