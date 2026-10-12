# CoisasComGosto

Laravel catalog application for CoisasComGosto (Viana do Castelo): a REST API, a
server-rendered storefront, and the owners' dashboard.

- Interactive API docs: **http://127.0.0.1:5000/api/docs**
- Raw OpenAPI schema: **http://127.0.0.1:5000/api/swagger.json**

---

## Getting started

The application runs on PHP 8.4 (FrankenPHP) and MySQL 8, both containerised.
All settings live in one `.env` file:

```bash
cp .env.example .env
composer install                             # the container serves ./vendor
php artisan key:generate                     # fills APP_KEY in .env
docker compose up --build                    # MySQL + the app on :5000
```

Migrations run when the container starts, so a fresh database gets the schema
and an existing one catches up before the first request. Load the development
catalogue with:

```bash
docker compose exec web php artisan db:seed
```

Accounts are made only from the console — every account can rewrite the whole
catalogue, so none comes from the open web:

```bash
docker compose exec web php artisan app:create-user hugo
```

The storefront is then at http://127.0.0.1:5000 and MySQL is exposed on :3306,
so a GUI client like DataGrip can connect to the same database the application
uses.

### Nothing here drops the accounts

`migrate:fresh`, `migrate:refresh`, `migrate:reset` and `db:wipe` are refused
outside the test suite (`DB::prohibitDestructiveCommands` in
`app/Providers/AppServiceProvider.php`). They drop every table, accounts
included, and once that locked the owners out of their own dashboard. `db:seed`
empties the catalogue tables and leaves `users` alone.

### Changing the schema

A schema change is a new file in `database/migrations/`:

```bash
php artisan make:migration add_something_to_products
php artisan migrate                  # or restart the container
php artisan migrate:status
```

There is no `down` in practice: a migration that turns out wrong is corrected by
another one, which is the only undo that survives having already run somewhere.

The first migration, `2026_10_04_000000_create_catalogue_schema.php`, builds the
whole catalogue as the Flask app left it. Run against a database the Flask app
built, it adopts it instead and changes nothing, provided that database had
reached the Flask migration 0013; anything older is refused.

### Photographs are never deleted by the application

Removing a photograph in the dashboard marks its row
(`product_images.deleted_at`, Eloquent's soft delete) and leaves the file where
it is. Deleting a piece or a colour removes the rows — a marked photograph of a
colour that no longer exists is a state nothing could present — and still leaves
the files. Replacing a collection cover leaves the one it replaced.

The reason is that the owners' only copy of a photograph may be the one they
uploaded from a phone two years ago. A mis-tap must be recoverable; the
confirmations name the count, and a confirmation is not a backup.

One command collects the leftovers, and it is the only thing in the project that
deletes a file:

```bash
docker compose exec web php artisan app:sweep-uploads --dry-run   # list, change nothing
docker compose exec web php artisan app:sweep-uploads             # after 30 days
docker compose exec web php artisan app:sweep-uploads --days=7
```

It purges rows marked longer ago than the window, then removes files no row
points at — counting a marked photograph and every collection cover as in use.
Age is read off the file's own mtime rather than any row, since an upload whose
request failed after the file was written has no row at all and must not be
collected while a request is still running. Nothing calls it automatically; run
it by hand or from cron.

Putting a photograph back is `ProductImage::withTrashed()->find($id)->restore()`.
There is no button for it yet: the row is kept so that recovery is possible at
all.

Uploads are decoded and re-encoded with GD (Intervention Image) before they are
stored. That is how a file proves it is an image, and it is what strips the EXIF
a phone writes into a photograph — including where it was taken.

### Configuration

`.env` is read by both docker compose and the application. `.env.example` is the
committed template; `.env` itself is gitignored. Real environment variables always
beat the file, which is how compose overrides `MYSQL_HOST` to `db`.

| Variable | Default | Purpose |
|---|---|---|
| `APP_DEBUG` | `true` | Full errors with stack traces. Never `true` in production |
| `APP_KEY` | — | Encrypts the session cookie. `php artisan key:generate` |
| `JWT_SECRET_KEY` | dev value | Signs the API's bearer tokens. **The app refuses to serve on the dev value, or none, with `APP_DEBUG` off** |
| `JWT_ACCESS_MINUTES` | `15` | Access-token lifetime |
| `JWT_REFRESH_DAYS` | `14` | Refresh-token lifetime |
| `SESSION_DRIVER` | `cookie` | The session is an encrypted cookie: no table, no files |
| `CACHE_STORE` | `file` | Holds the login and storefront-event rate limits |
| `MYSQL_HOST` | `127.0.0.1` | Compose overrides this to `db` |
| `MYSQL_PORT` | `3306` | |
| `MYSQL_USER` / `MYSQL_PASSWORD` | `coisascomgosto` | Application account |
| `MYSQL_DATABASE` | `coisascomgosto` | |
| `MYSQL_ROOT_PASSWORD` | `root` | Bootstraps the MySQL container |
| `WEB_PORT` | `5000` | Host port |

The app reads the same `MYSQL_*` names the MySQL container bootstraps itself
from, so there is one set of credentials rather than a `DB_*` copy that can drift.

### Live reload

docker-compose.yml bind-mounts the project, and PHP reads the files on every
request, so a saved file is live on the next page load with no rebuild. A
rebuild is only needed when the Dockerfile or `docker/php.ini` changes:

```bash
docker compose up -d --build web
```

### Deploying

Production is one small Linux server running the same image as development,
through `compose.prod.yml`. Everything below is done once. After that, every
push to `main` that passes the checks goes live on its own, through the
`deploy` job in `.github/workflows/checks.yml`.

1. **A server.** Any Ubuntu 24.04 machine with 2 GB of memory or more; an OVH
   VPS-1 or a Hetzner CX23 does. Create it with your SSH public key
   (`~/.ssh/id_ed25519.pub`), and have backups on: they cover the database and
   the photographs together. In its firewall allow inbound TCP 22, 80 and 443,
   and UDP 443.
2. **DNS.** At the registrar, an `A` record for each domain and one for its `www`,
   both pointing at the server's address.
3. **Set it up**, from your own machine, in the project folder:

   ```bash
   ssh root@ADDRESS sh -s coisascomgosto.pt < deploy/setup-server.sh
   ```

   On OVH, whose images log you in as `ubuntu`, it is
   `ssh ubuntu@ADDRESS sudo sh -s coisascomgosto.pt < deploy/setup-server.sh`.
   The script installs Docker, makes a `deploy` user, clones `main` to
   `/srv/coisascomgosto`, writes a `.env` with freshly generated secrets, starts
   the stack and prints a key. The site answers over HTTPS within a minute of
   the DNS reaching the server.
4. **Let GitHub deploy.** In the repository's *Settings › Secrets and variables ›
   Actions*, add what the script printed: the variables `DEPLOY_HOST` and
   `DEPLOY_USER`, and the secret `DEPLOY_SSH_KEY`.
5. **Accounts** are made on the server, as in development:

   ```bash
   ssh deploy@ADDRESS
   cd /srv/coisascomgosto && docker compose -f compose.prod.yml exec web php artisan app:create-user NAME
   ```

What the production stack does differently, for whoever changes it:

- `APP_ENV=production` and `APP_DEBUG=false`. The entrypoint then runs
  `php artisan optimize`, so config, routes and views are compiled once.
- `APP_KEY` and a `JWT_SECRET_KEY` of its own, 32 bytes or more. The app refuses
  to serve on the placeholder.
- **Volumes on `public/static/img/products` and `public/static/img/collections`.**
  Uploaded photographs are written there; in a container without one they are
  gone at the next deploy.
- `SERVER_NAME` holds the domain, and FrankenPHP's Caddy serves it on 80 and
  443 with a certificate it fetches and renews itself. The session cookie is
  `Secure` outside debug, so plain HTTP would not keep anyone signed in. Nothing
  sits in front, so `TRUSTED_PROXIES` stays empty; put a proxy there and it
  needs that proxy's address, or every visitor shares one storefront-events
  rate limit.

### Running outside Docker

Only MySQL needs the container:

```bash
docker compose up -d db
composer install
php artisan migrate
php artisan serve --port=5000
```

### Tests

The suite is [Pest](https://pestphp.com) against a real MySQL server rather than
a stand-in, so the SQL that ships is the SQL that is tested:

```bash
docker compose up -d db
npm ci && npx playwright install chromium     # once, for the browser tests
vendor/bin/pest                               # everything
vendor/bin/pest tests/Feature                 # without a browser
```

`phpunit.xml` points the suite at `coisascomgosto_test`, and `tests/TestCase.php`
refuses any database whose name does not end in `_test`, because the first test
runs `migrate:fresh`. Every test starts from the schema's own rows: tables are
truncated rather than rolled back, so ids start at 1 and the browser tests'
server sees what the test wrote. `docker/mysql/01-grant-test-schema.sql` gives the
application account rights over `*_test` schemas so the suite needs no root
credentials; it runs automatically when the MySQL volume is first created.

Set `MYSQL_DATABASE=something_test` in the shell to run two suites side by side.

#### The front end

The front end is tested in a browser rather than by reading its source. Tests
that grepped a JavaScript file passed whether the page worked or not, and failed
whenever a line moved. The dialogs, the catalogue, the gallery and the dashboard
are driven for real with Pest's browser plugin, which runs Chromium through
Playwright — the only reason the project has a `package.json`. The app itself has
no Node build: Bootstrap, Font Awesome, PhotoSwipe and SweetAlert2 are vendored
under `public/static/`.

A browser rather than jsdom, because jsdom has no `HTMLDialogElement.showModal()`,
which is what `core/modal.js` is built on, and no cascade — so it cannot see the
bugs these dialogs actually hit.

#### CI

`.github/workflows/checks.yml` runs the whole suite on every push to `main` or
`dev` and on every pull request, against a real MySQL service, with Chromium
installed so the browser tests run rather than skip.

---

## Domain model

A product sits at the centre of several independent layers.

```
product type ──┐                        (required: what the object IS)
materials ─────┤                        (what it is made OF: none, one or several)
default size ──┴──► product ──► variant ──► colour set ──► colours
                        │                     │
                        └──► sizes            └──► collections
                                                   (a set is gathered by any
                                                    number of them, and that is
                                                    the only way a piece is in
                                                    one)
```

| Layer | Meaning | Example |
|---|---|---|
| **Product type** | What the object *is*. Required. | `Caixa`, `Moldura`, `Coração`, `Presépio Minhoto` |
| **Material** | What it is made *of*, and a piece may be made of several: Manel e Maria is a wooden base with figures of modelling paste. Maintained by the owners. | `Madeira`, `Pasta de modelar` |
| **Collection** | A themed grouping. It gathers colour sets rather than owning them, and reaches a piece only through the colour sets that piece is offered in — there is no collection on a piece. | `Barra da Saia` |
| **Colour** | A single named swatch, optionally with a hex code. | `Branco`, `Dourado` |
| **Colour set** | A named combination of **two or more** colours, shared: it may be gathered by several collections, or by none. | `Preto e Branco`, `Preto Floral` |
| **Variant** | One product offered in one colour set. | A `Caixa Redonda` in `Red and White` |
| **Size** | `Pequeno` / `Médio` / `Grande`, seeded by the schema. | — |

### Worked example

A **Caixa Redonda** in the **Barra da Saia** collection, sold in four colour
combinations, is *one* product with *four* variants:

```
Caixa Redonda
├── variants
│   ├── White and Green   (colours: White, Green)   — gathered by Barra da Saia
│   ├── Red and White     (colours: Red, White)
│   ├── Blue and White    (colours: Blue, White)
│   └── White and Gray    (colours: White, Gray)
├── default_size: Médio
└── sizes: Pequeno, Médio, Grande
```

### Storage model

Relationships are integer columns with an index on each, and **every one of them
carries a `FOREIGN KEY`**. Every cascade is also written in the models
(`remove()` on `Product`, `ColorSet`, `ProductVariant` and `Collection`, and the
controllers' deletes): the models are the behaviour, the constraints are the
backstop for a direct `DELETE` that bypasses them.

| Deleting… | …does this | and the constraint |
|---|---|---|
| material | takes it off the pieces made of it; they survive, keeping any other material | `CASCADE` on the join |
| collection | unlinks its colour sets, which survive, possibly in other collections; that is also what takes its pieces out of it | `CASCADE` on the join |
| colour | removes it from every colour set | `CASCADE` |
| colour set | deletes the variants using it, and their photographs' rows | `CASCADE` |
| size | unlinks it from products, clears it as any default size | `CASCADE`, `SET NULL` |
| product type | refused while any piece uses it — `409` with the count | `RESTRICT` |
| product | deletes its photographs' rows, sizes, materials and variants | `CASCADE` |
| variant | deletes its photographs' rows | `CASCADE` |

`RESTRICT` on `products.type_id` is the one that is not a cascade: `type_id` is
`NOT NULL`, so there is no unfiled-piece state to fall back on.

### Rules worth knowing

- A product needs a **product type** — the one fact every piece has. Materials
  and default size are optional.
- **Materials are a lookup the owners maintain** from the dashboard. A piece may
  be made of more than one, so `/api/products/` takes `material_ids` and the
  material facet counts can add up to more than the catalogue holds.
- **Types are flat.** The shape of a piece lives in its own name ("Caixa
  Redonda", "Caixa de Joias") rather than in a level above it.
- **A colour set name is unique across the catalogue.** One combination is named
  once and shared: `Preto e Branco` is the same two colours whether Filigrana or
  Bordados shows it, and both may gather it.
- A product with **no listed sizes** is sold only in its default size. Sizes are
  replaced wholesale via `PUT`, never appended.

---

## API reference

Every endpoint, field and status code is generated by
[Scramble](https://scramble.dedoc.co) from the routes, the validation rules and
the API resources, and served at **`/api/docs`**, with the raw OpenAPI document
at `/api/swagger.json`. This section covers only what a schema cannot tell you.

All routes are prefixed with `/api`. A trailing slash is accepted and ignored.

### Authentication

The API uses **JWT bearer tokens**.

```
POST /auth/login     { username, password }         -> { access_token, refresh_token, user }
POST /auth/refresh   (REFRESH token in header)      -> { access_token }
GET  /auth/me        (access token in header)       -> the caller's account
POST /auth/logout                                   -> ends the browser's session
```

```bash
ACCESS=$(curl -s -X POST localhost:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"hugo","password":"..."}' | jq -r .access_token)

curl -H "Authorization: Bearer $ACCESS" localhost:5000/api/users/
```

| Token | Lifetime | Purpose |
|---|---|---|
| **access** | 15 min (`JWT_ACCESS_MINUTES`) | Sent with every request |
| **refresh** | 14 days (`JWT_REFRESH_DAYS`) | Exchanged for a new access token |

When the access token expires, the client POSTs to `/auth/refresh` with the
**refresh** token and retries — no password prompt. An access token sent there is
refused. Tokens are HS256 over `JWT_SECRET_KEY` (`app/Support/Jwt.php`) and carry
the claims flask-jwt-extended wrote — `sub` as a string id, `type`, and
`username` — so tokens issued before the move to Laravel kept working.

Catalog **reads are public** — the storefront depends on that. Every **write**,
plus all of `/users`, `/contacts` and `/analytics`, is guarded by
`app/Http/Middleware/AuthenticateApi.php`, and answers `401` with JSON rather than
redirecting: its callers are API clients and `fetch()` requests.

**There is one kind of account.** Two people run this workshop, both sign in to
the same dashboard, and everything it does is something either of them may do —
so there are no roles. Password hashes are never returned. Accounts created by
the Flask app carry Werkzeug scrypt hashes; the first right password checks one
the slow way (`app/Support/LegacyScrypt.php`, about three seconds) and replaces it
with bcrypt.

> **Why the guard also accepts the session.** The dashboard's pages are rendered
> server-side and gated by Laravel's session, because a page load cannot carry a
> token from localStorage. Login therefore signs the browser in alongside issuing
> the tokens, and the guard accepts either — which is what lets the dashboard's
> own scripts call plain `fetch()` with no token handling.
>
> **A session-authenticated write also needs `X-Requested-With`.** The browser
> attaches the cookie to any request to this origin, including one made by a page
> belonging to somebody else. A cross-site HTML form cannot set a header at all,
> and a cross-site `fetch()` that sets one asks for a preflight this API does not
> answer — so the header's presence is proof the request came from our own code.
> `core/api.js` sends it on every request. This stands in for Laravel's CSRF
> token on the API routes.
>
> **Why login answers 404 and 401 differently.** The login page asks for the
> username first and the password on a second screen, and decides which screen to
> draw from the status: 404 says there is no such account, 401 asks for the
> password. That tells anyone which names have accounts, which is the price of
> the two-step page. The first step sends no password, and is not counted as a
> failed attempt.
>
> **Wrong guesses are counted.** Five failures against one username inside
> fifteen minutes and the next attempt answers `429`, right password included. A
> successful sign-in clears the record, and refusals are not counted, so someone
> who keeps knocking cannot hold the lockout open. Laravel's `RateLimiter` keeps
> the count in `CACHE_STORE`.

### Conventions

**Pagination** — every list endpoint accepts `page` (1-based, default 1) and
`limit` (default 10, max 100), and wraps its rows alongside:

```json
{ "pagination": { "total": 42, "page": 2, "pages": 5, "limit": 10 } }
```

Non-numeric or non-positive values return `400`. The dashboard's product list
pages with `page`; the other screens still load whole lists, so `core/api.js`
compares `pagination.total` against what arrived and throws rather than
rendering a count that is quietly short; the cap is `Controller::MAX_LIMIT`.
Counts those screens show (`pieces` on collections and colour sets, products
without photographs via `has_photos=0`) come from the server, not from the list.

**Search** — list endpoints accept `q` for a case-insensitive substring match on
name.

**Status codes**

| Code | Meaning |
|---|---|
| `200` / `201` / `204` | Success |
| `400` | Missing or wrongly typed body fields (`{"message", "errors"}`), bad pagination, or a refused upload |
| `401` | Wrong password, a username sent without one, or a missing/invalid/expired token and no session |
| `403` | A session-authenticated write with no `X-Requested-With` header |
| `404` | The resource, or something it references, does not exist |
| `409` | Name (or variant) already taken, or a type still in use |
| `429` | Too many failed logins for this username, or storefront events from this address |

Every error body has a `message`. An optional field sent as `null` is refused
like any other wrong type: omit it instead.

### Behaviour the schema does not show

- **`color_ids` is ordered.** The first colour is the primary one — it is what
  the storefront badge tints itself with. Duplicates are collapsed.
- **Variants, images and sizes are sub-resources**, not fields on the product
  body: `POST /products/<id>/variants`, `/images`, and `PUT /sizes`.
- **Every image belongs to a colour set**, through its required `variant_id`.
  `primary_image` is the first photograph of the first colour that has one.
- **`POST /products/<id>/images/upload`** takes `multipart/form-data` and stores
  the file under `public/static/img/products/`.
- **Contacts is a singleton**: one row, always id 1, edited in place. `PUT` is a
  full replacement, so an omitted field is cleared. The WhatsApp number *is* the
  phone number; `whatsapp_url` is derived from it by stripping every non-digit.
- **Events**: `starts_on`/`ends_on` are ISO dates and `ends_on` is omitted for a
  one-day event. The timeline renders the range in Portuguese
  (`App\Support\Format::eventDates`), collapsing shared parts — `12 - 20 de
  Agosto de 2025`, but `28 de Julho - 3 de Agosto de 2025`.
- **`/storefront-events`** is the one public write outside `/auth`. It answers
  `204` and nothing else, drops ids that do not exist rather than refusing them,
  and stores no identifier of the visitor.

---

## Storefront

Server-rendered pages (Blade) that read the JSON API from the browser, so the
catalogue has a single source of truth.

| Page | Route | What it does |
|---|---|---|
| Landing | `/` | Hero, story, product families, events timeline and contacts |
| Catalog | `/products` | Filter sidebar + product grid |
| Product | `/products/<id>` | Image previewer + thumbnails + details |
| Not found | any unmatched path | Custom 404 keeping the site chrome |

**Styling is [Bootstrap](https://getbootstrap.com/) 5.3.8**, vendored at
`public/static/bootstrap/`. `public/static/css/theme.css` retints it through its
own `--bs-*` custom properties — no Sass build — and the store and dashboard
stylesheets add only what Bootstrap does not ship. Layout is Bootstrap's own grid,
and the navbar, offcanvas sidebar, dropdown, tabs, pagination and modal parts are
the framework's; the one exception is the modal element itself, a native
`<dialog>` wearing Bootstrap's `.modal-*` classes, because the browser's top layer
keeps a confirmation raised from inside a dialog in front of it.

Error pages (`resources/views/errors/`) extend the storefront layout; anything
under `/api` gets a JSON body instead.

---

## Project layout

```
app/
  Http/Controllers/Api/ The REST API: validation, status codes, one per resource
  Http/Controllers/     The storefront's home page; the base Controller has the
                        paging, 404 and 409 helpers the API shares
  Http/Middleware/      AuthenticateApi — bearer token or session, on every write
  Http/Resources/       The JSON shape of each resource
  Models/               Eloquent models: relations, filters, and the deletes
                        that must take rows with them
  Support/              Jwt, Uploads, TypeIcons, Format, LegacyScrypt
bootstrap/app.php       Middleware and error rendering
config/                 Only what differs from Laravel's defaults
database/
  migrations/           The schema
  seeders/              The development catalogue, and the schema's own rows
docker/                 php.ini, the entrypoint, and MySQL's first-start grant
public/static/          CSS, JS, images and the photographs, served as-is
resources/views/        Blade templates
routes/                 web.php, api.php, and console.php (the app:* commands)
tests/
  Feature/              HTTP-level tests
  Browser/              Chromium-driven tests of the pages and dialogs
docs/                   Written-down plans for work in progress
```
