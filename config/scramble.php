<?php

use Dedoc\Scramble\SecurityDocumentation\MiddlewareAuthSecurityStrategy;
use Dedoc\Scramble\Support\Generator\SecurityScheme;

return [
    'api_path' => 'api',

    'info' => [
        'version' => '2.0',
        'description' => "Catalog API for CoisasComGosto.\n\n"
            .'A product has a required **product type** and may also be made of several **materials**, '
            .'declare a **default size**, list the **sizes** it is available in, and carry **variants** — '
            .'one per **colour set** it is offered in. It is in a **collection** through those colour sets.'
            ."\n\n"
            .'Catalog reads are public. Every write, plus `/users` and `/contacts`, needs a **bearer token**: '
            .'POST `/auth/login` for a token pair, then `/auth/refresh` when the access token expires.',
    ],

    'ui' => [
        'title' => 'CoisasComGosto API',
    ],

    // Public, as they always were: the API they describe is the one the
    // storefront already calls in the open.
    'middleware' => ['web'],

    // A padlock on every operation behind AuthenticateApi, and none elsewhere.
    'security_strategy' => [
        MiddlewareAuthSecurityStrategy::class,
        [
            'middleware' => ['auth.api'],
            'scheme' => SecurityScheme::http('bearer', 'JWT')->as('Bearer'),
        ],
    ],
];
