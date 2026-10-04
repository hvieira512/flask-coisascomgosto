<?php

// The session cookie is a credential — AuthenticateApi accepts it in place of a
// bearer token — so it never travels over plain HTTP outside development, where
// there is no TLS to send it over. Everything else is Laravel's default:
// HttpOnly, and SameSite=Lax so the owners stay signed in when they arrive from
// a link in their mail.
return [
    'secure' => env('SESSION_SECURE_COOKIE', ! env('APP_DEBUG', false)),
];
