# Slim rather than alpine: PyMySQL is pure Python, but Werkzeug's scrypt
# hashing wants a real libssl, and musl builds of cryptography are a fight.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies first: this layer is cached until the requirements change.
COPY requirements.txt requirements-dev.txt ./

# The runtime image ships without pytest and friends. The test service in
# docker-compose.yml builds with INSTALL_DEV=true to get them.
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .

RUN chmod +x docker-entrypoint.sh

# Runs as a non-root user. Nothing in the image needs to be written at runtime.
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 5000

# The entrypoint picks the dev server or gunicorn from FLASK_DEBUG.
ENTRYPOINT ["./docker-entrypoint.sh"]
