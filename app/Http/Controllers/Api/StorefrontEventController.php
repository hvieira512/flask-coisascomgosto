<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Middleware\AuthenticateApi;
use App\Models\Product;
use App\Models\ProductVariant;
use App\Models\Size;
use App\Models\StorefrontEvent;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Validation\Rule;

/**
 * Recording what a visitor did — the one public write outside /auth.
 *
 * It answers 204 and nothing else: the page never reads the result, and a
 * counter that puts an error in a shopper's console is worse than one that
 * missed an event. So an id that does not exist is dropped rather than refused;
 * only a malformed request is a 400.
 */
class StorefrontEventController extends Controller
{
    // Sixty events from one address a minute. A visitor reading a piece sends
    // one view and maybe an enquiry; sixty is a flood.
    public const PER_MINUTE = 60;

    public function store(Request $request): Response
    {
        // First, before any work. The address is used here and never stored.
        $key = 'storefront-events:'.$request->ip();
        if (RateLimiter::tooManyAttempts($key, self::PER_MINUTE)) {
            $this->fail(429, 'Too many events. Slow down.');
        }
        RateLimiter::hit($key, 60);

        // A crawler cannot set a header outside the CORS safelist, and a
        // cross-site form cannot set one at all.
        if (! $request->hasHeader(AuthenticateApi::REQUIRED_HEADER)) {
            $this->fail(403, AuthenticateApi::REQUIRED_HEADER.' header required');
        }

        $data = $this->payload($request, [
            'kind' => ['present', 'string', Rule::in(StorefrontEvent::KINDS)],
            'product_id' => ['sometimes', 'integer:strict'],
            'variant_id' => ['sometimes', 'integer:strict'],
            'size_id' => ['sometimes', 'integer:strict'],
            'facet' => ['sometimes', 'string'],
            'facet_label' => ['sometimes', 'string'],
            'term' => ['sometimes', 'string'],
            'results' => ['sometimes', 'integer:strict'],
        ]);

        $productId = $data['product_id'] ?? null;
        if ($productId !== null && ! Product::whereKey($productId)->exists()) {
            // Deleted between the page loading and this arriving, or somebody
            // poking at the endpoint. Nothing to count, nothing to say.
            return response()->noContent();
        }

        // Keep the enquiry, forget a colour that is not one of the piece's own.
        $variantId = $data['variant_id'] ?? null;
        if ($variantId !== null && ($productId === null
            || ! ProductVariant::where(['id' => $variantId, 'product_id' => $productId])->exists())) {
            $variantId = null;
        }

        $sizeId = $data['size_id'] ?? null;
        if ($sizeId !== null && ! Size::whereKey($sizeId)->exists()) {
            $sizeId = null;
        }

        $label = $data['facet_label'] ?? '';
        $term = $data['term'] ?? '';

        StorefrontEvent::create([
            'kind' => $data['kind'],
            'product_id' => $productId,
            'variant_id' => $variantId,
            'size_id' => $sizeId,
            'facet' => $data['facet'] ?? null,
            // A label is a name the owners gave something, so it keeps its case.
            // A search term is lowercased so two spellings do not split a count.
            'facet_label' => $label !== '' ? StorefrontEvent::tidy($label) : null,
            'term' => $term !== '' ? mb_strtolower(StorefrontEvent::tidy($term)) : null,
            'results' => $data['results'] ?? null,
        ]);

        return response()->noContent();
    }
}
