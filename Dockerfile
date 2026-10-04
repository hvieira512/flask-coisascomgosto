# FrankenPHP: Caddy and PHP in one process, so one container serves the app the
# way gunicorn did, with no separate nginx or PHP-FPM to configure.
FROM dunglas/frankenphp:1-php8.4

# gd re-encodes uploaded photographs (which is what strips the EXIF a phone
# writes into them); pdo_mysql is the database; zip is how Composer unpacks.
RUN install-php-extensions gd pdo_mysql opcache zip

COPY docker/php.ini /usr/local/etc/php/conf.d/app.ini
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /app

# Dependencies first: this layer is cached until composer.lock changes.
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-scripts --no-autoloader --no-interaction --prefer-dist

COPY . .
RUN composer dump-autoload --optimize --no-dev \
    && chmod +x docker/entrypoint.sh

# Runs as a non-root user. Only storage/, bootstrap/cache and the photograph
# folders are written at runtime.
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app/storage /app/bootstrap/cache /app/public/static/img /data /config
USER app

# Plain HTTP on 8000; TLS, when there is any, belongs to whatever sits in front.
ENV SERVER_NAME=:8000
EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["frankenphp", "run", "--config", "/etc/frankenphp/Caddyfile"]
