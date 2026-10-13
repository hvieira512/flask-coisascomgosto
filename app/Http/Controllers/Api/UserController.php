<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\UserResource;
use App\Models\User;
use Illuminate\Http\Request;

/** The accounts. Every endpoint needs a signed-in caller. */
class UserController extends Controller
{
    public function index(Request $request): array
    {
        [$page, $limit, $offset] = $this->paging($request);

        return [
            'users' => UserResource::collection(User::orderBy('id')->offset($offset)->limit($limit)->get())->resolve($request),
            'pagination' => $this->envelope(User::count(), $page, $limit),
        ];
    }

    public function show(int $user): UserResource
    {
        return new UserResource($this->findOr404(User::class, $user, 'User'));
    }
}
