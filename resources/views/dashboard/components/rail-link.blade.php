<a href="{{ route($route, absolute: false) }}"
   class="dash-rail-link d-flex align-items-center justify-content-between gap-3 px-2 py-2 text-decoration-none"
   @if (request()->routeIs($route)) aria-current="page" @endif>
    <span>{{ $label }}</span>
    @if ($count !== null)<span class="count data fs-7">{{ $count }}</span>@endif
</a>
