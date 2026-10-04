<?php

use App\Http\Controllers\StoreController;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Route;

Route::get('/', [StoreController::class, 'home'])->name('store.home');
Route::view('/products', 'store.products')->name('store.products');
Route::get('/products/{product}', [StoreController::class, 'product'])->whereNumber('product')->name('store.product');

Route::view('/auth', 'auth.index')->middleware('guest')->name('login');

Route::get('/logout', function (Request $request) {
    Auth::logout();
    $request->session()->invalidate();

    return redirect()->route('store.home');
})->name('logout');

// Each page is a shell its own script fills from the API.
Route::middleware('auth')->prefix('dashboard')->name('dashboard.')->group(function () {
    Route::redirect('/', '/dashboard/home');
    Route::view('/home', 'dashboard.home')->name('home');
    Route::view('/products', 'dashboard.products')->name('products');
    Route::view('/events', 'dashboard.events')->name('events');
    Route::view('/types', 'dashboard.types')->name('types');
    Route::view('/colors', 'dashboard.colors')->name('colors');
    Route::view('/collections', 'dashboard.collections')->name('collections');
    Route::view('/contacts', 'dashboard.contacts')->name('contacts');
});
