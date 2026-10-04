<!DOCTYPE html>
<html lang="pt" data-bs-theme="light" class="@yield('html_class')">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'CoisasComGosto')</title>
    <link href="/static/img/logo.png" rel="icon" type="image/png">
    <link href="/static/bootstrap/bootstrap.min.css" rel="stylesheet">
    <link href="/static/css/theme.css" rel="stylesheet">
    @yield('styles')
    <script src="/static/fontawesome/a38dd6e785.js" crossorigin="anonymous"></script>
    @yield('head')
</head>

<body class="@yield('body_class')">
    @include('components.loader')

    @yield('body')

    <script src="/static/bootstrap/bootstrap.bundle.min.js"></script>

    <script type="module" src="/static/js/store/loader.js"></script>
    @yield('scripts')
</body>

</html>
