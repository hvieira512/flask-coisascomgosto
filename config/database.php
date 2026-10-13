<?php

// Read from the MYSQL_* names because the MySQL container bootstraps itself from
// the same .env: one set of credentials, not a DB_* copy that can drift from it.
return [

    'default' => 'mysql',

    'connections' => [
        'mysql' => [
            'driver' => 'mysql',
            'host' => env('MYSQL_HOST', '127.0.0.1'),
            'port' => env('MYSQL_PORT', '3306'),
            'database' => env('MYSQL_DATABASE', 'coisascomgosto'),
            'username' => env('MYSQL_USER', 'coisascomgosto'),
            'password' => env('MYSQL_PASSWORD', 'coisascomgosto'),
            'unix_socket' => '',
            'charset' => 'utf8mb4',
            'collation' => 'utf8mb4_unicode_ci',
            'prefix' => '',
            'prefix_indexes' => true,
            'strict' => true,
            'engine' => 'InnoDB',
        ],
    ],

    'migrations' => [
        'table' => 'migrations',
        'update_date_on_publish' => true,
    ],

];
