<p class="timeline-date">
    {{ \App\Support\Format::eventDates($event->starts_on, $event->ends_on) }}
</p>

<h3 class="h6 mb-1">
    @if ($event->url)
    <a href="{{ $event->url }}" target="_blank" rel="noopener">{{ $event->name }}</a>
    @else
    {{ $event->name }}
    @endif
</h3>

@if ($event->location)
<p class="fs-7 text-body-secondary mb-2">{{ $event->location }}</p>
@endif

@if ($event->description)
<p class="fs-7 text-body-secondary">{{ $event->description }}</p>
@endif
