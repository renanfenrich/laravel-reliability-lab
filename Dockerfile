FROM composer:2.8.12 AS composer
FROM php:8.4.26-cli-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev libxml2-dev libonig-dev unzip && docker-php-ext-install -j4 pdo_pgsql pcntl mbstring dom xml xmlwriter && rm -rf /var/lib/apt/lists/*
COPY --from=composer /usr/bin/composer /usr/local/bin/composer
WORKDIR /app
COPY composer.json composer.lock* ./
RUN composer install --no-scripts --no-interaction --prefer-dist
COPY . .
RUN mkdir -p storage/framework/cache storage/framework/sessions storage/framework/views storage/logs bootstrap/cache && chown -R 1000:1000 /app
USER 1000:1000
EXPOSE 8080
CMD ["php","artisan","serve","--host=0.0.0.0","--port=8080"]
