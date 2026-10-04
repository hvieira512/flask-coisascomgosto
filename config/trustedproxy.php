<?php

// Read by Laravel's own TrustProxies: comma-separated addresses or CIDRs, or *.
return [
    'proxies' => env('TRUSTED_PROXIES'),
];
