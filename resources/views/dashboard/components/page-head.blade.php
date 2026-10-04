{{-- With $buttonId, the header carries the page's one action and a count line the page's script fills. --}}
<header class="d-flex flex-wrap align-items-end justify-content-between gap-4 pb-3 mb-4 border-bottom">
    <div>
        <p class="eyebrow">{{ $eyebrow }}</p>
        <h1 class="font-display dash-title mb-0">{{ $title }}</h1>
        @isset($buttonId)
        <p class="text-body-secondary mt-2 mb-0" id="{{ $countId }}">—</p>
        @elseif (! empty($subtitle))
        <p class="text-body-secondary mt-2 mb-0">{{ $subtitle }}</p>
        @endisset
    </div>
    @isset($buttonId)
    <button class="btn btn-dark" id="{{ $buttonId }}">
        <span class="icon"><i class="fa-solid {{ $icon ?? 'fa-plus' }}"></i></span>
        <span>{{ $buttonLabel }}</span>
    </button>
    @endisset
</header>
