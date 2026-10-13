<?php

// The session cookie is a credential — AuthenticateApi accepts it in place of a
// bearer token — so it never travels over plain HTTP outside development, where
// there is no TLS to send it over. HttpOnly and SameSite=Lax are Laravel's
// defaults; Lax keeps the owners signed in when they arrive from a link in
// their mail.
return [
    'secure' => env('SESSION_SECURE_COOKIE', ! env('APP_DEBUG', false)),

    // Signed in until the browser closes, as the dashboard always was, rather
    // than logged out two hours into an afternoon of photographing pieces.
    'expire_on_close' => true,
    'lifetime' => 14 * 24 * 60,
];
