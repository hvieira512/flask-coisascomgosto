<?php

return [
    // Signs the API's bearer tokens. Never the value .env.example ships outside
    // debug: AppServiceProvider refuses to boot on it.
    'secret' => env('JWT_SECRET_KEY'),

    // Short-lived access, long-lived refresh: a leaked access token expires
    // quickly while the owner stays signed in.
    'access_minutes' => (int) env('JWT_ACCESS_MINUTES', 15),
    'refresh_days' => (int) env('JWT_REFRESH_DAYS', 14),
];
