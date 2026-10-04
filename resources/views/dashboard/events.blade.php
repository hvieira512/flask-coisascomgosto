@extends('layouts.dashboard')

@section('page_title', 'Eventos')

@section('content')
@include('dashboard.components.page-head', ['eyebrow' => 'Percurso', 'title' => 'Eventos',
    'countId' => 'event-count', 'buttonId' => 'new-event', 'buttonLabel' => 'Novo evento'])

<div>
    <div class="dash-table-wrap">
        <table class="table dash-table is-wide table-hover" id="event-table">
            <thead>
                <tr>
                    <th class="dash-col-name">Evento</th>
                    <th>Local</th>
                    <th>Datas</th>
                    <th class="dash-col-actions"><span class="visually-hidden">Acções</span></th>
                </tr>
            </thead>
            <tbody id="event-rows"></tbody>
        </table>
    </div>
</div>

@include('dashboard.components.modal', ['id' => 'newEventModal', 'title' => 'Novo evento'])
@include('dashboard.components.modal', ['id' => 'editEventModal', 'title' => 'Editar evento'])
@include('dashboard.components.modal', ['id' => 'deleteEventModal', 'title' => 'Apagar evento'])
@endsection

@section('page_scripts')
<script type="module" src="/static/js/dashboard/events/main.js"></script>
@endsection
