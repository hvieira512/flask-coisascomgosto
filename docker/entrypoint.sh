#!/bin/sh
# Bring the schema up to date before serving, so a container started against an
# older database catches up instead of serving against a schema the code no
# longer matches. --isolated takes a cache lock so two runs cannot apply the same
# migration at once.
#
# ponytail: the lock lives in CACHE_STORE, which is the container's own files, so
# it only serialises runs inside one container. There is one web container; with
# more, set CACHE_STORE=database (and add Laravel's cache tables) so they share it.
set -e

php artisan migrate --force --isolated

exec "$@"
