#!/bin/sh
# Chooses a server based on FLASK_DEBUG, so one image covers both development
# and production instead of maintaining two Dockerfiles.
#
#   FLASK_DEBUG=1  Flask's dev server: live reload and the interactive debugger.
#                  docker-compose.yml bind-mounts the source, so a saved file
#                  reloads the container without a rebuild.
#   otherwise      gunicorn, which is what should ever face the internet.
set -e

case "${FLASK_DEBUG}" in
    1 | true | True | TRUE)
        echo "Starting Flask development server (live reload, debugger ON)"
        exec flask --app "${FLASK_APP:-app}" run \
            --host 0.0.0.0 --port 5000 --debug
        ;;
esac

echo "Starting gunicorn with ${GUNICORN_WORKERS:-3} workers"
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --access-logfile - \
    app:app
