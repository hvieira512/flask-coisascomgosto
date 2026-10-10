{{-- The logo's butterfly, drawn in one line. Each stroke carries pathLength="1"
     so the loader can draw it on with a dash. Colour comes from currentColor. --}}
<svg class="{{ $class ?? '' }}" viewBox="0 0 120 120" fill="none" stroke="currentColor"
     stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"
     aria-hidden="true" focusable="false">
    <path class="body" pathLength="1" d="M55 40C53 56 53 70 55 86"/>
    <path class="wing" pathLength="1" d="M55 46C42 28 10 22 12 44C13 60 38 64 55 58"/>
    <path class="wing" pathLength="1" d="M55 46C68 28 100 22 98 44C97 60 72 64 55 58"/>
    <path class="wing wing-lower" pathLength="1" d="M55 60C40 66 16 82 24 96C30 106 48 98 55 84"/>
    <path class="wing wing-lower" pathLength="1" d="M55 60C70 66 94 82 86 96C80 106 62 98 55 84"/>
    <path class="curl" pathLength="1" d="M26 44c-6-4 0-12 6-8 3 2 1 6-2 6"/>
    <path class="curl" pathLength="1" d="M84 44c6-4 0-12-6-8-3 2-1 6 2 6"/>
    <path class="antenna" pathLength="1" d="M38 20C45 19 52 28 54 40"/>
    <path class="antenna" pathLength="1" d="M72 20C65 19 58 28 56 40"/>
    <circle class="tip" cx="38" cy="20" r="2.4" fill="currentColor" stroke="none"/>
    <circle class="tip" cx="72" cy="20" r="2.4" fill="currentColor" stroke="none"/>
</svg>
