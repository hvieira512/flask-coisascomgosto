<?php

use App\Http\Controllers\Api\AnalyticsController;
use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\CollectionController;
use App\Http\Controllers\Api\ColorController;
use App\Http\Controllers\Api\ColorSetController;
use App\Http\Controllers\Api\ContactController;
use App\Http\Controllers\Api\EventController;
use App\Http\Controllers\Api\MaterialController;
use App\Http\Controllers\Api\ProductController;
use App\Http\Controllers\Api\ProductImageController;
use App\Http\Controllers\Api\ProductSizeController;
use App\Http\Controllers\Api\ProductTypeController;
use App\Http\Controllers\Api\ProductVariantController;
use App\Http\Controllers\Api\SizeController;
use App\Http\Controllers\Api\StorefrontEventController;
use App\Http\Controllers\Api\UserController;
use Illuminate\Support\Facades\Route;

// Catalogue reads are public. Every write, plus /users and /contacts, needs a
// bearer token or the dashboard's session — see AuthenticateApi.

$lookup = function (string $path, string $controller) {
    Route::get($path, [$controller, 'index']);
    Route::get("{$path}/{id}", [$controller, 'show'])->whereNumber('id');

    Route::middleware('auth.api')->group(function () use ($path, $controller) {
        Route::post($path, [$controller, 'store']);
        Route::put("{$path}/{id}", [$controller, 'update'])->whereNumber('id');
        Route::delete("{$path}/{id}", [$controller, 'destroy'])->whereNumber('id');
    });
};

$lookup('product-types', ProductTypeController::class);
$lookup('materials', MaterialController::class);
$lookup('collections', CollectionController::class);
$lookup('colors', ColorController::class);
$lookup('color-sets', ColorSetController::class);
$lookup('sizes', SizeController::class);
$lookup('events', EventController::class);

Route::get('products/facets', [ProductController::class, 'facets']);
$lookup('products', ProductController::class);

Route::get('collections/{id}/color-sets', [CollectionController::class, 'colorSets'])->whereNumber('id');
Route::get('products/{id}/variants', [ProductVariantController::class, 'index'])->whereNumber('id');
Route::get('products/{id}/images', [ProductImageController::class, 'index'])->whereNumber('id');
Route::get('products/{id}/sizes', [ProductSizeController::class, 'index'])->whereNumber('id');

Route::middleware('auth.api')->group(function () {
    Route::put('collections/{id}/color-sets', [CollectionController::class, 'replaceColorSets'])->whereNumber('id');
    Route::post('collections/{id}/cover', [CollectionController::class, 'storeCover'])->whereNumber('id');
    Route::delete('collections/{id}/cover', [CollectionController::class, 'destroyCover'])->whereNumber('id');

    Route::post('products/{id}/variants', [ProductVariantController::class, 'store'])->whereNumber('id');
    Route::delete('products/{id}/variants/{variant}', [ProductVariantController::class, 'destroy'])->whereNumber(['id', 'variant']);

    Route::post('products/{id}/images', [ProductImageController::class, 'store'])->whereNumber('id');
    Route::post('products/{id}/images/upload', [ProductImageController::class, 'upload'])->whereNumber('id');
    Route::put('products/{id}/images/{image}', [ProductImageController::class, 'update'])->whereNumber(['id', 'image']);
    Route::delete('products/{id}/images/{image}', [ProductImageController::class, 'destroy'])->whereNumber(['id', 'image']);

    Route::put('products/{id}/sizes', [ProductSizeController::class, 'update'])->whereNumber('id');

    Route::get('contacts', [ContactController::class, 'show']);
    Route::put('contacts', [ContactController::class, 'update']);

    Route::get('users', [UserController::class, 'index']);
    Route::get('users/{id}', [UserController::class, 'show'])->whereNumber('id');

    Route::get('auth/me', [AuthController::class, 'me']);
    Route::get('analytics/overview', [AnalyticsController::class, 'overview']);
});

Route::post('auth/register', [AuthController::class, 'register']);
Route::post('auth/login', [AuthController::class, 'login']);
Route::post('auth/refresh', [AuthController::class, 'refresh']);
Route::post('auth/logout', [AuthController::class, 'logout']);

Route::post('storefront-events', [StorefrontEventController::class, 'store']);

Route::fallback(fn () => response()->json(['message' => 'Resource not found'], 404));
