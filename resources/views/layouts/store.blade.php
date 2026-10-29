@extends('layouts.base')

@section('title', $__env->yieldContent('page_title').' · Coisas com Gosto')

@section('styles')
<link rel="stylesheet" href="/static/css/store.css">
@endsection

@section('body')
@include('store.components.navbar')

<main>
    @yield('content')
</main>

@include('store.components.footer')
@endsection

@section('scripts')
<script type="module" src="/static/js/store/timeline.js"></script>
<script type="module" src="/static/js/store/visit.js"></script>
@yield('page_scripts')
@endsection
