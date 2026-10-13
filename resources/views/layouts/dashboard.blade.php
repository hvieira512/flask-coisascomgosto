@extends('layouts.base')

@section('title', $__env->yieldContent('page_title', 'Painel').' · Painel')

@section('body_class', 'dashboard-body')

@section('styles')
<link rel="stylesheet" href="/static/css/dashboard.css">
@endsection

@section('body')
@include('dashboard.components.sidebar')

<div class="dash-work d-flex flex-column">
    @include('dashboard.components.navbar', ['where' => trim($__env->yieldContent('page_title', 'Painel'))])

    <section class="p-3 p-md-4 p-xl-5 pb-5 flex-grow-1">
        @yield('content')
    </section>
</div>
@endsection

@section('scripts')
<script src="/static/sweetalert2/sweetalert2.all.min.js"></script>
@yield('page_scripts')
@endsection
