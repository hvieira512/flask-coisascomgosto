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
wipes existing data, apart from the user accounts, which it carries across.

### Changing the schema

`db/schema.sql` is the current shape of the database and what a fresh install is
built from. A database that already exists is brought forward by the migrations
in `db/migrations/`:

```bash
docker compose exec web flask migrate            # apply whatever is pending
docker compose exec web flask migrate --status   # list applied and pending
```

Migrations run automatically when the container starts, so a deploy against an
older database catches up before it serves a request.

**A schema change needs both halves:**

1. edit `db/schema.sql`, so new databases and the test suite get it;
2. add `db/migrations/NNNN_what_it_does.sql`, so existing databases get it.

`init-db` records every migration as applied without running it, because a
database built from `schema.sql` is by definition already current — so the two
halves never fight. For a database that predates the system but is already up to
date, `flask migrate --stamp` does the same thing. There is no `down`: a
migration that turns out wrong is corrected by another one, which is the only
undo that survives having already run somewhere.

### Configuration

`.env` is read by both docker compose and the application, so there is a single
place to change a setting. `.env.example` is the committed template; `.env`
itself is gitignored and must never be committed. Real environment variables
always beat the file, which is how compose overrides `MYSQL_HOST` to `db`
inside the network.

| Variable | Default | Purpose |
|---|---|---|
| `FLASK_DEBUG` | `1` | `1` gives live reload and the debugger; anything else runs gunicorn |
| `SECRET_KEY` | dev value | Signs the dashboard's session cookie. **Change in production** |
| `JWT_SECRET_KEY` | falls back to `SECRET_KEY` | Signs the API's bearer tokens. **Change in production**, 32+ bytes |
| `JWT_ACCESS_MINUTES` | `15` | Access-token lifetime |
| `JWT_REFRESH_DAYS` | `14` | Refresh-token lifetime |
| `MYSQL_HOST` | `127.0.0.1` | Compose overrides this to `db` |
| `MYSQL_PORT` | `3306` | |
| `MYSQL_USER` / `MYSQL_PASSWORD` | `coisascomgosto` | Application account |
| `MYSQL_DATABASE` | `coisascomgosto` | |
| `MYSQL_ROOT_PASSWORD` | `root` | Bootstraps the MySQL container |
| `WEB_PORT` | `5000` | Host port |
| `GUNICORN_WORKERS` | `3` | Ignored when `FLASK_DEBUG=1` |

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
product type ──┐                        (required: what the object IS)
  └─ sub-type  │                          one level deep
material ──────┤                        (optional: what it is made OF)
collection ────┼──► product ──► variant ──► colour set ──► colours
               │        │                     ▲
default size ──┘        └──► sizes            └── normally owned by a collection
```

| Layer | Meaning | Example |
|---|---|---|
| **Product type** | What the object *is*. Required. | `Caixa`, `Moldura`, `Coração`, `Presépio Minhoto` |
| **Material** | What it is made *of*. Optional, and maintained by the owners. | `Madeira`, `Tecido` |
| **Sub-type** | How that object is finished or used. Exactly one level deep. | A `Coração` **with string** to hang, or as a **base for mini figures** |
| **Collection** | A themed grouping that owns colour sets. | `Barra da Saia` |
| **Colour** | A single named swatch, optionally with a hex code. | `White`, `Green` |
| **Colour set** | A named combination of colours, normally owned by a collection. | `White and Green` |
| **Variant** | One product offered in one colour set. | A `Caixa Redonda` in `Red and White` |
| **Size** | `Pequeno` / `Médio` / `Grande`, seeded by the schema. | — |

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
like `products.type_id` use them).

**Every cascade lives in the repository layer**, not the database:

| Deleting… | …does this, in `api/repositories/` |
|---|---|
| material | clears `material_id` on the pieces made of it; they survive |
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

- A product needs a **product type** — the one fact every piece has. Material,
  collection and default size are optional.
- **Materials are a lookup the owners maintain** from the dashboard, so the list
  grows with the workshop rather than with a migration.
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

Every endpoint, field, status code and example body is generated from the
flask-restx models and served at **`/api/docs`** (Swagger UI), with the raw
schema at `/api/swagger.json`. That is the reference; this section covers only
what a schema cannot tell you.

All routes are prefixed with `/api`.

### Authentication

The API uses **JWT bearer tokens**.

```
POST /auth/register  { username, email, password }  -> the new account
POST /auth/login     { username, password }         -> { access_token, refresh_token, user }
POST /auth/refresh   (REFRESH token in header)      -> { access_token }
GET  /auth/me        (access token in header)       -> the caller's account
POST /auth/logout                                   -> clears the rendered session
```

```bash
ACCESS=$(curl -s -X POST localhost:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"hugo","password":"..."}' | jq -r .access_token)

curl -H "Authorization: Bearer $ACCESS" localhost:5000/api/users/
```

In `/api/docs` the **Authorize** button sends the same header, so every padlocked
endpoint can be exercised from the docs.

| Token | Lifetime | Purpose |
|---|---|---|
| **access** | 15 min (`JWT_ACCESS_MINUTES`) | Sent with every request |
| **refresh** | 14 days (`JWT_REFRESH_DAYS`) | Exchanged for a new access token |

**When the access token expires**, the client POSTs to `/auth/refresh` with the
**refresh** token and retries — no password prompt. An *access* token sent to
`/auth/refresh` is rejected with `422`; only a refresh token is accepted there.
Tokens carry `username` and `is_admin` claims, so a guard needs no database round
trip.

Catalog **reads are public** — the storefront depends on that. Every **write**,
plus all of `/users` and `/contacts`, is guarded by `auth_required` in
`api/security.py`, and answers `401` with JSON rather than redirecting: its
callers are API clients and `fetch()` requests, either of which would otherwise
be handed a login page to parse as a payload.

`is_admin` is **not** accepted at registration, so nobody can self-promote.
Password hashes are never returned.

> **Why `auth_required` also accepts a session.** The dashboard's pages are
> rendered server-side and gated by Flask's session cookie, because a page load
> cannot carry a token from localStorage. Login therefore sets the cookie
> alongside issuing the tokens, and the guard accepts either — which is what lets
> the dashboard's own scripts call plain `fetch()` with no token handling, while
> the documented token flow stays intact for API clients. `web/dashboard.py` has
> its own `login_required` for the pages, and that one *does* redirect: a browser
> following a link wants the login form, not a 401.
>
> JWTs are stateless, so `/auth/logout` clears the session but cannot revoke an
> issued token — the client discards it. Set both `SECRET_KEY` and
> `JWT_SECRET_KEY` in production; the defaults are placeholders, and
> `JWT_SECRET_KEY` should be 32+ bytes.

### Conventions

**Pagination** — every list endpoint accepts `page` (1-based, default 1) and
`limit` (default 10, max 100), and wraps its rows alongside:

```json
{ "pagination": { "total": 42, "page": 2, "pages": 5, "limit": 10 } }
```

Non-numeric or non-positive values return `400`.

**Search** — list endpoints accept `q` for a case-insensitive substring match on
name.

**Status codes**

| Code | Meaning |
|---|---|
| `200` / `201` | Success |
| `400` | Missing/invalid body fields, bad pagination, or illegal type nesting |
| `401` | Wrong password, or a missing/expired access token and no session |
| `403` | Authenticated, but the account lacks the required privilege |
| `422` | Malformed token, or the wrong token type for the endpoint |
| `404` | The resource, or something it references, does not exist |
| `409` | Name (or variant) already taken |

### Behaviour the schema does not show

- **`color_ids` is ordered.** The first colour is the primary one — it is what
  the storefront badge tints itself with. Duplicates are collapsed.
- **`Pequeno`, `Médio` and `Grande` are seeded** by `db/schema.sql`, ordered by
  `position` rather than by id. The list is the owners' to extend.
- **Variants, images and sizes are sub-resources**, not fields on the product
  body: `POST /products/<id>/variants`, `/images`, and `PUT /sizes`.
- **`PUT /products/<id>/sizes` replaces the whole list**; `{"size_ids": []}` puts
  a product back to its default size only.
- **An image with a `variant_id` belongs to that colour set**; without one it
  belongs to the product and acts as the fallback. `primary_image` is the first
  product-level photo, falling back to the first variant photo — so a product
  photographed only per colour set still gets a grid tile.
- **`POST /products/<id>/images/upload`** takes `multipart/form-data` instead of
  JSON, and stores the file under `static/img/products/`. Everything else about
  an image row is identical either way.
- **Contacts is a singleton**: one row, always id 1, edited in place. No id in
  the path, no POST, no DELETE. `PUT` is a full replacement, so an omitted field
  is cleared. There is deliberately no `phone` field — the WhatsApp number *is*
  the phone number, and `whatsapp_url` is derived from it by stripping every
  non-digit, so `+351 912 345 678` becomes `https://wa.me/351912345678`. The
  navbar and footer read it through an app-wide context processor
  (`web/__init__.py`), so the owners change their details in one place.
- **Events**: `starts_on`/`ends_on` are ISO dates and `ends_on` is omitted for a
  one-day event. The timeline renders the range in Portuguese via the
  `event_dates` Jinja filter, collapsing shared parts — `12 - 20 de Agosto de
  2025`, but `28 de Julho - 3 de Agosto de 2025`.

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

- Filters live in the sidebar: search, material, product type (with sub-types
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
app.py                  Flask app entrypoint + the init-db, migrate, seed and
                        create-admin commands
config.py               Config read from environment variables

api/
  __init__.py           Api object; mounts every namespace under /api
  db.py                 PyMySQL connection handling and schema init
  migrations.py         The numbered-.sql runner behind `flask migrate`
  pagination.py         Request-arg parsing and the pagination envelope
  security.py           auth_required — bearer token or session, on every write
  uploads.py            Storing uploaded photographs on disk
  models/               flask-restx marshalling models — these ARE the Swagger docs
  repositories/         Every SQL statement in the application, one class per table
    base.py             The reads the lookup tables share
  routes/               HTTP concerns only: validation, status codes, marshalling
    crud.py             The route bodies they share: paging, 404, 409
    products/           One namespace, four modules: the product itself, its
                        variants, its photographs, its sizes
  type_icons.py         Name -> Font Awesome class, the one copy of that table

web/                    Server-rendered storefront and dashboard blueprints
templates/  static/     Jinja templates and assets
db/schema.sql           Full schema, dropped and recreated by init-db
db/migrations/          Numbered .sql files, each applied once, in order
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
