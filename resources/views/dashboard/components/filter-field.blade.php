<div class="col">
    <label class="form-label" for="{{ $id }}">{{ $label }}</label>
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
</div>
