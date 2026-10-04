<div class="col">
    <label class="form-label fs-7" for="{{ $id }}">{{ $label }}</label>
    <div class="input-group input-group-sm">
        @isset($options)
        <select class="form-select form-select-sm" id="{{ $id }}">
            @foreach ($options as [$value, $text])
            <option value="{{ $value }}">{{ $text }}</option>
            @endforeach
        </select>
        @else
        <input class="form-control form-control-sm" id="{{ $id }}"
               placeholder="{{ $placeholder ?? '' }}">
        @endisset
        <span class="input-group-text"><i class="{{ $icon ?? 'fa-solid fa-filter' }}" aria-hidden="true"></i></span>
    </div>
</div>
