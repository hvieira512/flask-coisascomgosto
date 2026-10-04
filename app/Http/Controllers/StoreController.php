<?php

namespace App\Http\Controllers;

use App\Models\Event;
use App\Models\ProductType;
use Illuminate\View\View;

class StoreController extends Controller
{
    // Seven families and the "ver tudo" tile fill two rows of four.
    private const TYPES_LIMIT = 7;

    private const TIMELINE_LIMIT = 12;

    public function home(): View
    {
        $productTypes = ProductType::withPieces()->orderBy('id')->limit(self::TYPES_LIMIT)->get();
        ProductType::attachCovers($productTypes);

        return view('store.home', [
            'productTypes' => $productTypes,
            'events' => Event::orderByDesc('starts_on')->orderByDesc('id')->limit(self::TIMELINE_LIMIT)->get(),
        ]);
    }

    public function product(int $product): View
    {
        return view('store.product', ['productId' => $product]);
    }
}
