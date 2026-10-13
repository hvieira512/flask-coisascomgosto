<?php

namespace App\Models;

use App\Support\LegacyScrypt;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Support\Facades\Hash;

class User extends Authenticatable
{
    public $timestamps = false;

    protected $fillable = ['username', 'email', 'password'];

    protected $hidden = ['password'];

    protected $rememberTokenName = false;

    protected function casts(): array
    {
        return ['created_at' => 'datetime'];
    }

    /**
     * Whether $password is this account's. Accounts created by the Flask app
     * carry a Werkzeug scrypt hash; the first right answer replaces it with
     * bcrypt, so each one is checked the slow way exactly once.
     */
    public function checkPassword(string $password): bool
    {
        if (LegacyScrypt::owns($this->password)) {
            if (! LegacyScrypt::check($password, $this->password)) {
                return false;
            }
            $this->forceFill(['password' => Hash::make($password)])->save();

            return true;
        }

        return Hash::check($password, $this->password);
    }
}
