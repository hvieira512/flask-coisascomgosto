# CoisasComGosto

Flask catalog application for CoisasComGosto (Viana do Castelo) — a REST API
plus a server-rendered dashboard.

- Interactive API docs (Swagger UI): **http://127.0.0.1:5000/api/docs**
- Raw OpenAPI schema: **http://127.0.0.1:5000/api/swagger.json**

---

## Getting started

The application runs on Flask and MySQL 8, both containerised. All settings
live in one `.env` file:

```bash
cp .env.example .env                         # then edit if you like
docker compose up --build                    # MySQL + the app on :5000
docker compose exec web flask init-db        # create the schema, once
```

The storefront is then at http://127.0.0.1:5000 and MySQL is exposed on
:3306, so a GUI client like DataGrip can connect to the same database the
application uses.

`init-db` drops and recreates every table, so it is safe to re-run — and it
wipes existing data.

### Configuration

`.env` is read by both docker compose and the application, so there is a single
place to change a setting. `.env.example` is the committed template; `.env`
itself is gitignored and must never be committed. Real environment variables
always beat the file, which is how compose overrides `MYSQL_HOST` to `db`
inside the network.

| Variable | Default | Purpose |
|---|---|---|
| `FLASK_DEBUG` | `1` | `1` gives live reload and the debugger; anything else runs gunicorn |
| `SECRET_KEY` | dev value | Signs sessions. **Change in production** |
| `JWT_SECRET_KEY` | dev value | Signs tokens. **Change in production** |
| `JWT_ACCESS_MINUTES` | `15` | Access-token lifetime |
| `JWT_REFRESH_DAYS` | `14` | Refresh-token lifetime |
| `MYSQL_HOST` | `127.0.0.1` | Compose overrides this to `db` |
| `MYSQL_PORT` | `3306` | |
| `MYSQL_USER` / `MYSQL_PASSWORD` | `coisascomgosto` | Application account |
| `MYSQL_DATABASE` | `coisascomgosto` | |
| `MYSQL_ROOT_PASSWORD` | `root` | Bootstraps the MySQL container |
| `WEB_PORT` | `5000` | Host port |
| `GUNICORN_WORKERS` | `3` | Ignored when `FLASK_DEBUG=1` |
| `MAIL_*` | unset | Outgoing mail; disabled when unset |

### Live reload

With `FLASK_DEBUG=1` the container runs Flask's development server and
docker-compose.yml bind-mounts the source, so saving a file on the host
reloads the app — no rebuild. Set `FLASK_DEBUG=0` and the same image runs
gunicorn instead; `docker-entrypoint.sh` makes that choice at startup, which is
why there is only one Dockerfile.

> **Never run with `FLASK_DEBUG=1` in production.** Werkzeug's debugger hands a
> Python console to anyone who can reach the port.

A rebuild is only needed when dependencies change:

```bash
docker compose up -d --build web
```

### Running outside Docker

Only MySQL needs the container:

```bash
docker compose up -d db

python3 -m venv env                  # or: uv venv env --python 3.13 --seed
source env/bin/activate
pip install -r requirements.txt      # add -r requirements-dev.txt for tests

flask --app app init-db
flask --app app run --debug
```

`.env` still applies — `python-dotenv` loads it in `config.py` and `api/db.py`.

### Tests

The suite runs against a real MySQL server rather than a stand-in, so the SQL
that ships is the SQL that is tested:

```bash
docker compose run --rm test         # in Docker

docker compose up -d db              # or against a local interpreter
pytest
```

`tests/conftest.py` forces `MYSQL_DATABASE` to a name ending in `_test`,
because the session fixture calls `init_db()` and that drops every table. A
mistyped environment variable cannot point the suite at real data.
`db/init/01-grant-test-schema.sql` gives the application account rights over
`*_test` schemas so the suite needs no root credentials; it runs automatically
when the MySQL volume is first created.

---

## Domain model

A product sits at the centre of several independent layers.

```
category ──────┐                        (required: what shelf it lives on)
product type ──┤                        (optional: what the object IS)
  └─ sub-type  │                          one level deep
collection ────┼──► product ──► variant ──► colour set ──► colours
               │        │                     ▲
default size ──┘        └──► sizes            └── normally owned by a collection
```

| Layer | Meaning | Example |
|---|---|---|
| **Category** | Required taxonomy bucket. | `Madeira` |
| **Product type** | What the object *is*. | `Hairbrush`, `Picture frame`, `Wooden box`, `Coração` |
| **Sub-type** | How that object is finished or used. Exactly one level deep. | A `Coração` **with string** to hang, or as a **base for mini figures** |
| **Collection** | A themed grouping that owns colour sets. | `Barra da Saia` |
| **Colour** | A single named swatch, optionally with a hex code. | `White`, `Green` |
| **Colour set** | A named combination of colours, normally owned by a collection. | `White and Green` |
| **Variant** | One product offered in one colour set. | A `Caixa Redonda` in `Red and White` |
| **Size** | `S` / `M` / `L`, seeded by the schema. | — |

### Worked example

A **Caixa Redonda** in the **Barra da Saia** collection, sold in four colour
combinations, is *one* product with *four* variants:

```
Caixa Redonda
├── collection: Barra da Saia
├── variants
│   ├── White and Green   (colours: White, Green)
│   ├── Red and White     (colours: Red, White)
│   ├── Blue and White    (colours: Blue, White)
│   └── White and Gray    (colours: White, Gray)
├── default_size: M
└── sizes: S, M, L
```

### Storage model

The schema is **deliberately non-relational**: primary keys and indexes only,
**no `FOREIGN KEY` constraints**. Relationships are plain integer columns with
an index on each (13 explicit indexes; `EXPLAIN QUERY PLAN` confirms lookups
like `products.category_id` use them).

**Every cascade lives in the repository layer**, not the database:

| Deleting… | …does this, in `api/repositories/` |
|---|---|
| category | deletes its products (and their images, sizes, variants) |
| collection | clears `collection_id` on its colour sets and products |
| colour | removes it from every colour set |
| colour set | deletes variants using it, plus their images |
| size | unlinks it from products, clears it as any default size |
| product type | deletes sub-types, clears `type_id` on products |
| product | deletes its images, sizes and variants |
| variant | deletes its images |

> **The database no longer prevents orphans.** Anything writing outside
> `api/repositories/` — a manual SQL session, a future script — can leave
> dangling rows, and MySQL will not complain. The cascade tests in
> `tests/test_repositories.py` and `tests/test_catalog_api.py` are what keep
> this honest.

### Rules worth knowing

- A product needs a **category**; type, collection and default size are optional.
- **Types nest exactly one level.** Parenting a sub-type to another sub-type
  returns `400`. A type that already has sub-types cannot itself become one.
- Filtering products by a **parent type** also returns products filed under its
  sub-types, so `?type_id=<Coração>` returns both finishes.
- **Colour set names are unique per collection**, not globally — two collections
  may each have a `White and Green`.
- A product with **no listed sizes** is sold only in its default size. Sizes are
  replaced wholesale via `PUT`, never appended.
- Deleting a **collection** or **product type** does not delete its products;
  they survive with that field cleared. Deleting a **colour set** removes the
  variants that used it. Deleting a **product** removes its variants and sizes.

---

## API reference

All routes are prefixed with `/api`.

### Authentication

The API uses **JWT bearer tokens**. Catalog reads are public; `/users` and
`/contacts` require a token.

```
POST /auth/login    { username, password }  -> { access_token, refresh_token, user }
POST /auth/refresh  (refresh token in header) -> { access_token }
GET  /auth/me       (access token in header)  -> the caller's account
POST /auth/logout   clears the server-rendered session
```

Send the access token on every protected call:

```bash
curl -H "Authorization: Bearer $ACCESS_TOKEN" localhost:5000/api/users/
```

| Token | Lifetime | Purpose |
|---|---|---|
| **access** | 15 min (`JWT_ACCESS_MINUTES`) | Sent with every request |
| **refresh** | 14 days (`JWT_REFRESH_DAYS`) | Exchanged for a new access token |

**When the access token expires**, the client POSTs to `/auth/refresh` with the
**refresh** token and retries — no password prompt. An *access* token sent to
`/auth/refresh` is rejected (422); only a refresh token is accepted there.

`static/js/core/auth.js` implements this in the browser: `Auth.authFetch()`
attaches the access token, and on a 401 it refreshes once and replays the
request. Parallel 401s share one in-flight refresh. Only when the refresh token
is dead too is the user sent back to `/auth`.

Tokens carry `username` and `is_admin` claims, so guards need no database round
trip. `api/security.py` exposes `token_required` and `admin_required`.

> The rendered dashboard pages still authenticate by **Flask session**, which
> login sets alongside the tokens. JWTs are stateless, so `/auth/logout` clears
> the session but cannot revoke an issued token — the client discards it, which
> the dashboard does on sign-out. Set `JWT_SECRET_KEY` to 32+ bytes in
> production.

### Conventions

**Pagination** — every list endpoint accepts `page` (1-based, default 1) and
`limit` (default 10, max 100), and returns:

```json
{
  "pagination": { "total": 42, "page": 2, "pages": 5, "limit": 10 }
}
```

Non-numeric or non-positive values return `400`.

**Search** — list endpoints accept `q` for a case-insensitive substring match on
name.

**Status codes**

| Code | Meaning |
|---|---|
| `200` / `201` | Success |
| `400` | Missing/invalid body fields, bad pagination, or illegal type nesting |
| `401` | Wrong password, or a missing/expired bearer token |
| `403` | Valid token, but the account lacks the required privilege |
| `422` | Malformed token, or the wrong token type for the endpoint |
| `404` | The resource, or something it references, does not exist |
| `409` | Name (or variant) already taken |

### Categories

| Method | Path | Notes |
|---|---|---|
| `GET` | `/categories/` | `?q=` |
| `POST` | `/categories/` | `{ name }` |
| `GET` | `/categories/<id>` | |
| `PUT` | `/categories/<id>` | `{ name }` |
| `DELETE` | `/categories/<id>` | Cascades to its products |

### Product types

| Method | Path | Notes |
|---|---|---|
| `GET` | `/product-types/` | `?q=`, `?parent_id=`, `?roots_only=1` |
| `POST` | `/product-types/` | `{ name, description?, parent_id? }` |
| `GET` | `/product-types/<id>` | Includes `sub_types` |
| `PUT` | `/product-types/<id>` | `{ name, description?, parent_id? }` |
| `DELETE` | `/product-types/<id>` | Cascades to sub-types |

```bash
# A Coração, and the two ways it can be finished
curl -X POST localhost:5000/api/product-types/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"Coração","description":"Wooden Viana heart plaque"}'

curl -X POST localhost:5000/api/product-types/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"With string","parent_id":1}'

curl -X POST localhost:5000/api/product-types/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"Base for mini figures","parent_id":1}'
```

### Collections

| Method | Path | Notes |
|---|---|---|
| `GET` | `/collections/` | `?q=` |
| `POST` | `/collections/` | `{ name, description? }` |
| `GET` | `/collections/<id>` | |
| `PUT` | `/collections/<id>` | `{ name, description? }` |
| `DELETE` | `/collections/<id>` | Products and colour sets survive, unowned |

### Colours

| Method | Path | Notes |
|---|---|---|
| `GET` | `/colors/` | `?q=` |
| `POST` | `/colors/` | `{ name, hex? }` |
| `GET` | `/colors/<id>` | |
| `PUT` | `/colors/<id>` | `{ name, hex? }` |
| `DELETE` | `/colors/<id>` | Removed from any colour set that used it |

### Colour sets

| Method | Path | Notes |
|---|---|---|
| `GET` | `/color-sets/` | `?q=`, `?collection_id=` |
| `POST` | `/color-sets/` | `{ name, color_ids[], collection_id? }` |
| `GET` | `/color-sets/<id>` | |
| `PUT` | `/color-sets/<id>` | Replaces the colour list wholesale |
| `DELETE` | `/color-sets/<id>` | Removes variants offered in it |

`color_ids` is ordered — the first colour is the primary one. Duplicates are
collapsed.

```bash
curl -X POST localhost:5000/api/color-sets/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"White and Green","color_ids":[1,2],"collection_id":1}'
```

### Sizes

| Method | Path | Notes |
|---|---|---|
| `GET` | `/sizes/` | `?q=`; ordered by `position` |
| `POST` | `/sizes/` | `{ name, position? }` |
| `GET` | `/sizes/<id>` | |
| `PUT` | `/sizes/<id>` | `{ name, position? }` |
| `DELETE` | `/sizes/<id>` | Detached from products; defaults cleared |

`S`, `M` and `L` are seeded by `db/schema.sql`.

### Products

| Method | Path | Notes |
|---|---|---|
| `GET` | `/products/` | `?q=`, `?category_id=`, `?collection_id=`, `?type_id=` |
| `POST` | `/products/` | see body below |
| `GET` | `/products/<id>` | |
| `PUT` | `/products/<id>` | Same body; variants and sizes are separate |
| `DELETE` | `/products/<id>` | Cascades to variants and size links |

Request body — only `name`, `description` and `category_id` are required:

```json
{
  "name": "Caixa Redonda",
  "description": "Caixa de madeira redonda",
  "category_id": 1,
  "type_id": 3,
  "collection_id": 1,
  "default_size_id": 2
}
```

Response:

```json
{
  "id": 1,
  "name": "Caixa Redonda",
  "description": "Caixa de madeira redonda",
  "category":     { "id": 1, "name": "Madeira" },
  "type":         { "id": 3, "name": "With string",
                    "parent": { "id": 1, "name": "Coração" } },
  "collection":   { "id": 1, "name": "Barra da Saia" },
  "default_size": { "id": 2, "name": "M", "position": 2 },
  "sizes":    [ { "id": 1, "name": "S", "position": 1 } ],
  "variants": [
    {
      "id": 1,
      "color_set": {
        "id": 1,
        "name": "White and Green",
        "collection": { "id": 1, "name": "Barra da Saia" },
        "colors": [
          { "id": 1, "name": "White", "hex": "#FFFFFF" },
          { "id": 2, "name": "Green", "hex": "#2E7D32" }
        ]
      }
    }
  ]
}
```

`type`, `collection` and `default_size` are `null` when unset.

### Product variants

| Method | Path | Notes |
|---|---|---|
| `GET` | `/products/<id>/variants` | |
| `POST` | `/products/<id>/variants` | `{ color_set_id }` — `409` if already offered |
| `DELETE` | `/products/<id>/variants/<variant_id>` | `404` if the variant belongs to another product |

### Product images

| Method | Path | Notes |
|---|---|---|
| `GET` | `/products/<id>/images` | `?variant_id=` to narrow to one colour set |
| `POST` | `/products/<id>/images` | `{ url, alt?, position?, variant_id? }` |
| `PUT` | `/products/<id>/images/<image_id>` | Same body |
| `DELETE` | `/products/<id>/images/<image_id>` | |

An image with a `variant_id` belongs to that colour set; without one it belongs
to the product and acts as the fallback. `primary_image` on a product is the
first product-level photo, falling back to the first variant photo — so a
product photographed only per colour set still gets a grid tile.

```bash
# A photo of the white/green version specifically
curl -X POST localhost:5000/api/products/1/images \
  -H 'Content-Type: application/json' \
  -d '{"url":"/static/img/caixa-branco-verde.jpg","alt":"Caixa branco e verde","variant_id":1}'
```

### Product sizes

| Method | Path | Notes |
|---|---|---|
| `GET` | `/products/<id>/sizes` | |
| `PUT` | `/products/<id>/sizes` | `{ size_ids: [] }` — full replacement |

```bash
# Offer the product in S, M and L
curl -X PUT localhost:5000/api/products/1/sizes \
  -H 'Content-Type: application/json' -d '{"size_ids":[1,2,3]}'

# Back to default size only
curl -X PUT localhost:5000/api/products/1/sizes \
  -H 'Content-Type: application/json' -d '{"size_ids":[]}'
```

### Events

Fairs, markets and shows the workshop has attended. Reads are public — the
landing-page timeline uses them; writes need a bearer token.

| Method | Path | Notes |
|---|---|---|
| `GET` | `/events/` | `?q=` matches name or location. Most recent first. |
| `POST` | `/events/` | **Bearer token.** `{ name, starts_on, location?, description?, ends_on?, url? }` |
| `GET` | `/events/<id>` | |
| `PUT` | `/events/<id>` | **Bearer token.** |
| `DELETE` | `/events/<id>` | **Bearer token.** |

`starts_on`/`ends_on` are ISO dates; omit `ends_on` for a one-day event. `year`
is derived from `starts_on` for grouping. The timeline renders the range in
Portuguese via the `event_dates` Jinja filter, collapsing shared parts —
`12 - 20 de Agosto de 2025`, but `28 de Julho - 3 de Agosto de 2025`.

```bash
curl -X POST localhost:5000/api/events/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Feira de Artesanato","location":"Viana do Castelo",
       "starts_on":"2025-08-15","ends_on":"2025-08-20"}'
```

### Contacts

The shop's own details — a **singleton**: one row, always id 1, edited in place.
There is no ID in the path and no POST/DELETE.

| Method | Path | Notes |
|---|---|---|
| `GET` | `/contacts/` | **Bearer token required.** Address, email, WhatsApp, socials |
| `PUT` | `/contacts/` | **Bearer token required.** Full replacement; omitted fields are cleared |

```json
{
  "id": 1,
  "address": "Viana do Castelo, Portugal",
  "email": "geral@coisascomgosto.pt",
  "whatsapp": "939320334",
  "whatsapp_url": "https://wa.me/939320334",
  "facebook_url": "https://www.facebook.com/coisascomgosto.vianadocastelo/",
  "instagram_url": "https://www.instagram.com/coisascomgostovc/"
}
```

**There is deliberately no `phone` field.** The WhatsApp number *is* the phone
number; `whatsapp_url` is derived from it by stripping every non-digit, so
`+351 912 345 678` becomes `https://wa.me/351912345678`.

The navbar and footer read this via an app-wide context processor
(`web/__init__.py`), so the owners change their details in one place.

### Users and auth

| Method | Path | Notes |
|---|---|---|
| `POST` | `/auth/register` | `{ username, email, password }` |
| `POST` | `/auth/login` | `{ username, password }` → token pair + session cookie |
| `POST` | `/auth/refresh` | Refresh token in header → new access token |
| `GET` | `/auth/me` | **Bearer token required.** The caller's account |
| `POST` | `/auth/logout` | |
| `GET` | `/users/` | **Bearer token required.** Paginated |
| `GET` | `/users/<id>` | **Bearer token required.** |

`is_admin` is **not** accepted at registration; every account is created
non-admin so nobody can self-promote. Password hashes are never returned.

Both `/users` and `/contacts` are behind bearer tokens. The public site never
calls them: the footer and landing page read contacts server-side through the
context processor.

---

---

## Storefront

Two public, server-rendered pages that consume the JSON API from the browser, so
the catalog has a single source of truth.

| Page | Route | What it does |
|---|---|---|
| Landing | `/` | Hero, story, collections, work, events timeline and contacts |
| Catalog | `/products` | Filter sidebar + product grid |
| Product | `/products/<id>` | Image previewer + vertical thumbnail carousel + details |
| Not found | any unmatched path | Custom 404 keeping the site chrome |

**Styling is [Bulma](https://bulma.io/) 1.0.2**, vendored at
`static/bulma/bulma.min.css`. `static/css/store.css` adds only what Bulma does
not ship: the gallery, the thumbnail rail and the grid tiles.

Bootstrap has been removed from the project entirely — `static/bootstrap/` is
gone and the dashboard and login pages are on Bulma too. jQuery, toastr and
FontAwesome remain, since none of them depended on Bootstrap. Social icons are
inline SVG partials under `templates/store/components/`.

### Error pages

`errors/404.html` and `errors/500.html` extend the storefront base, so an error
still shows the navbar, footer and contact details. The handlers in `app.py`
check the request path: anything under `/api` gets a JSON body instead, so API
clients never receive HTML.

### Catalog

- Filters live in the sidebar: search, category, product type (with sub-types
  indented under their parent) and collection.
- Every applied filter renders as a Bulma
  [delete-tag](https://bulma.io/documentation/elements/tag/#delete-tag) reading
  `Group: Value ×`. Clicking the badge removes that filter; the sidebar and the
  badge row are two views of the same state.
- Filters are mirrored into the query string, so a filtered view is shareable
  and survives a reload.
- Selecting a parent type also matches products filed under its sub-types.

### Product page

- A vertical rail of thumbnails sits to the left of the previewer, with
  arrow buttons to scroll it; the active thumbnail is scrolled into view.
- The previewer reveals ‹ › arrows on hover which step through the images and
  wrap around. Arrow keys work once the previewer has focus, and the arrows are
  reachable via `:focus-visible` for keyboard users.
- Picking a colour swatch swaps the gallery to that variant's photos, falling
  back to the product-level images when a variant has none.

Front-end files:

```
static/js/store/api.js        fetch wrapper + HTML escaping
static/js/store/filters.js    filter state, URL sync, badge labels
static/js/store/products.js   sidebar, badges and the grid
static/js/store/gallery.js    previewer + thumbnail rail
static/js/store/product.js    detail page wiring
```

---

## Project layout

```
app.py                  Flask app factory-ish entrypoint + the init-db command
config.py               Config read from environment variables
extensions.py           CORS and Mail extension instances

api/
  __init__.py           Api object; mounts every namespace under /api
  db.py                 Connection handling, PRAGMA foreign_keys, schema init
  pagination.py         Request-arg parsing and the pagination envelope
  models/               flask-restx marshalling models — these ARE the Swagger docs
  repositories/         Every SQL statement in the application, one class per table
  routes/               HTTP concerns only: validation, status codes, marshalling

web/                    Server-rendered dashboard blueprints
templates/  static/     Jinja templates and assets
db/schema.sql           Full schema, dropped and recreated by init-db
tests/                  pytest suite, isolated per test by truncating tables
```

### Layering rules

- **Routes never contain SQL.** They validate input, call repositories, and map
  outcomes to status codes.
- **Repositories never import Flask.** They take a MySQL cursor and return
  plain dicts, which makes them directly unit-testable.
- **`get_db_connection()` owns the transaction** — it commits on success and
  rolls back on exception, so handlers don't call `commit()` themselves.
- The schema has **no foreign keys**; cascades are implemented in the
  repositories. See *Storage model* above.
