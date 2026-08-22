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
older database catches up before it serves a request. Because that means two
containers can reach the runner at the same moment, a run holds a MySQL advisory
lock (`GET_LOCK`) and reads the pending list inside it: the second one waits, then
finds the ledger already written and applies nothing. Without that both would run
the same file, and the loser fails against a schema MySQL has already committed —
DDL cannot roll back. A run that cannot take the lock within ten seconds says so
and exits non-zero rather than proceeding.

**A schema change needs both halves:**

1. edit `db/schema.sql`, so new databases and the test suite get it;
2. add `db/migrations/NNNN_what_it_does.sql`, so existing databases get it.

`init-db` records every migration as applied without running it, because a
database built from `schema.sql` is by definition already current — so the two
halves never fight. For a database that predates the system but is already up to
date, `flask migrate --stamp` does the same thing. There is no `down`: a
migration that turns out wrong is corrected by another one, which is the only
undo that survives having already run somewhere.

### Photographs are never deleted by the application

Removing a photograph in the dashboard marks its row (`product_images.deleted_at`)
and leaves the file where it is. Deleting a piece or a colour removes the rows —
a marked photograph of a colour that no longer exists is a state nothing could
present — and still leaves the files. Replacing a collection cover leaves the one
it replaced.

The reason is that the owners' only copy of a photograph may be the one they
uploaded from a phone two years ago. Every one of those actions used to unlink the
file in the same request, so a mis-tap was unrecoverable; the confirmations name
the count, and a confirmation is not a backup.

One command collects the leftovers, and it is the only thing in the project that
deletes a file:

```bash
docker compose exec web flask sweep-uploads --dry-run   # list, change nothing
docker compose exec web flask sweep-uploads             # after 30 days
docker compose exec web flask sweep-uploads --days 7
```

It purges rows marked longer ago than the window, then removes files no row
points at — including a marked one, because a marked photograph is restorable and
its file is still in use. Age is read off the file's own mtime rather than any
row, since an upload whose request failed after the file was written has no row at
all and must not be collected while a request is still running. Nothing calls it
automatically; run it by hand or from cron.

Putting a photograph back is one `UPDATE` — `ProductImageRepository.restore()`.
There is no button for it yet, and that is the honest state of it: the row is kept
so that recovery is possible at all.

### Configuration

`.env` is read by both docker compose and the application, so there is a single
place to change a setting. `.env.example` is the committed template; `.env`
itself is gitignored and must never be committed. Real environment variables
always beat the file, which is how compose overrides `MYSQL_HOST` to `db`
inside the network.

| Variable | Default | Purpose |
|---|---|---|
| `FLASK_DEBUG` | `1` | `1` gives live reload and the debugger; anything else runs gunicorn |
| `SECRET_KEY` | dev value | Signs the dashboard's session cookie. **The app refuses to start on the dev value unless `FLASK_DEBUG=1`** |
| `JWT_SECRET_KEY` | falls back to `SECRET_KEY` | Signs the API's bearer tokens. Same refusal; 32+ bytes |
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

#### The frontend

The front end is tested in a browser rather than by reading its source. Tests
that grepped a JavaScript file for the endpoints it calls or the markup it builds
passed whether the page worked or not, and failed whenever a line moved; they are
gone. The dialogs — the create wizard and the modal helpers under
`static/js/core/` — are driven for real:

```bash
playwright install chromium     # once; the browser is not a pip package
pytest tests/test_dialog_behaviour.py
```

Without that browser the module skips, so the suite stays green for anyone who
has not installed it. A browser rather than jsdom for two reasons: jsdom has no
`HTMLDialogElement.showModal()`, which is what `core/modal.js` is built on, and no
cascade — so it cannot see the bugs these dialogs actually hit. `back.hidden =
true` once did nothing at all, because a class rule set its own `display` and
outranked the attribute, and only a real layout notices that the button is still
there.

#### Appearance

The rest of the suite tests geometry and never appearance, and the difference has
cost real defects: a modal card that rendered transparent, colour-set names
invisible because a line-height collapsed them, a 32px list indent, photo slots at
three times their size, hover underlines the design never had. Every one was found
by eye, on a screenshot, after the tests had gone green.

```bash
SCREENSHOTS=1 pytest tests/test_appearance.py        # compare with the baselines
SCREENSHOTS=update pytest tests/test_appearance.py   # recapture them
```

Eleven pages at two widths, downscaled to 240px wide and compared with the PNGs in
`tests/baselines/`. Downscaled deliberately: a full-resolution comparison fails on
font anti-aliasing and would be switched off within a week, while this still fails
loudly on anything the eye would notice. On the machine that captured them the
difference is 0.00% on every page, so the threshold is 0.1%; retinting one colour
token trips 21 of the 22 views, and deleting `.section`'s padding trips the phone
pages by 43–100%.

**Opt-in, and not run by CI.** Chromium renders text differently on macOS and on
Linux, so a baseline captured on one fails on the other — committing baselines that
match one machine would leave the suite red for everybody else. This is a check the
person changing the design runs, and the honest scope of it. Only the first 1400
compared pixels of each page are looked at, which is the fold and a good way past
it.

#### Types, and CI

```bash
pyright                              # 0 errors, and it stays that way
```

`pyrightconfig.json` sets `venvPath`/`venv` so the checker uses `env/` — without
it, pyright picks whichever interpreter it finds and reports every dependency as
unresolved, which was 79 of the 108 findings it first produced on a project whose
imports all work.

`.github/workflows/checks.yml` runs `pytest` and `pyright` on every push to
`main` or `dev` and on every pull request, against a real MySQL service. Two
things about it are deliberate:

- It builds a virtualenv at `./env`, the path `pyrightconfig.json` names, so one
  configuration means the same thing in CI and on a developer's machine.
- It installs Chromium and then *checks that it launched*. Without the browser
  the hundred-odd browser tests skip themselves and the run still goes green,
  which is worse than failing — a skipped test that looks like a passing one is
  how a broken dialog ships.

It also passes `SECRET_KEY` and `JWT_SECRET_KEY`, because `FLASK_DEBUG=0` there
and `config.py` refuses to start on the values `.env.example` ships.

---

## Domain model

A product sits at the centre of several independent layers.

```
product type ──┐                        (required: what the object IS)
material ──────┤                        (optional: what it is made OF)
collection ────┼──► product ──► variant ──► colour set ──► colours
               │        │                     ▲
default size ──┘        └──► sizes            └── gathered by any number
                                                  of collections
```

| Layer | Meaning | Example |
|---|---|---|
| **Product type** | What the object *is*. Required. | `Caixa`, `Moldura`, `Coração`, `Presépio Minhoto` |
| **Material** | What it is made *of*. Optional, and maintained by the owners. | `Madeira`, `Tecido` |
| **Collection** | A themed grouping. It gathers colour sets rather than owning them. | `Barra da Saia` |
| **Colour** | A single named swatch, optionally with a hex code. | `Branco`, `Dourado` |
| **Colour set** | A named combination of **two or more** colours, shared: it may be gathered by several collections, or by none. | `Preto e Branco`, `Preto Floral` |
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

Relationships are integer columns with an index on each, and **every one of them
also carries a `FOREIGN KEY`** (added in migration `0006`, against a database
that had no orphan row in it).

**Every cascade is still written in the repository layer**, and that is not
redundancy to be tidied away: a repository delete returns the URLs of the
photographs whose rows it removed, so the route can delete the files, which a
database cascade cannot do. The repositories are the behaviour; the constraints
are the backstop for the one direct `DELETE` that bypasses them. Each rule below
matches the method beside it.

| Deleting… | …does this, in `repositories/` | and the constraint |
|---|---|---|
| material | clears `material_id` on the pieces made of it; they survive | `SET NULL` |
| collection | unlinks its colour sets (they survive, possibly in other collections) and clears `collection_id` on its products | `CASCADE` on the join, `SET NULL` on products |
| colour | removes it from every colour set | `CASCADE` |
| colour set | deletes variants using it, plus their images | `CASCADE` |
| size | unlinks it from products, clears it as any default size | `CASCADE`, `SET NULL` |
| product type | refused while any piece uses it — `409` with the count | `RESTRICT` |
| product | deletes its images, sizes and variants | `CASCADE` |
| variant | deletes its images | `CASCADE` |

`RESTRICT` on `products.type_id` is the one that is not a cascade: `type_id` is
`NOT NULL`, so there is no unfiled-piece state to fall back on. The 409 with the
count of pieces still using the type is what the owners see; the constraint stops
the same thing happening behind the API's back.

### Rules worth knowing

- A product needs a **product type** — the one fact every piece has. Material,
  collection and default size are optional.
- **Materials are a lookup the owners maintain** from the dashboard, so the list
  grows with the workshop rather than with a migration.
- **Types are flat.** They nested one level until migration `0001`; the shape of
  a piece lives in its own name ("Caixa Redonda", "Caixa de Joias") rather than
  in a level above it.
- **A colour set name is unique across the catalogue.** One combination is named
  once and shared: `Preto e Branco` is the same two colours whether Filigrana or
  Bordados shows it, and both may gather it. Until migration `0009` a set had one
  owning collection and the name was unique only within it, which is what produced
  `Azul e Branco` and `Branco e Azul` for the same pair — the seed now has one set
  that both collections gather.
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
Tokens carry a `username` claim, so saying who acted needs no database round trip.

Catalog **reads are public** — the storefront depends on that. Every **write**,
plus all of `/users` and `/contacts`, is guarded by `auth_required` in
`api/security.py`, and answers `401` with JSON rather than redirecting: its
callers are API clients and `fetch()` requests, either of which would otherwise
be handed a login page to parse as a payload.

**There is one kind of account.** Two people run this workshop, both sign in to
the same dashboard, and everything it does is something either of them may do — so
there are no roles. The `users` table carried an `is_admin` flag for a while that
nothing ever read; it is gone, and a role system would be a column with a default
rather than a redesign. Password hashes are never returned.

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
> issued token — the client discards it.
>
> **Why login answers 404 and 401 differently.** The login page asks for the
> username first and the password on a second screen, and decides which screen to
> draw from the status: 404 offers to create the account, 401 asks for the
> password. So the endpoint tells you who has an account — which is acceptable
> here, since the same page openly offers registration, and the accounts belong to
> the two people who run the business.
>
> That first step sends the username with **no password**, and the endpoint
> answers without touching the stored hash. It used to send the password `"fake"`,
> which made every visit to /auth a failed login: a wasted scrypt on the server,
> and once wrong guesses started being counted, five page loads from locking the
> owners out of their own dashboard.
>
> **Wrong guesses are counted.** Five failures against one username inside
> fifteen minutes and the next attempt answers `429`, right password included —
> the point of a lockout is that the next guess is not tried. A successful sign-in
> clears the record, the window drains on its own, and refusals are not counted,
> so someone who keeps knocking cannot hold the lockout open. `api/rate_limit.py`
> keeps this in process memory: the count is per gunicorn worker and resets with
> the app, which is honest for one or two workers and is the seam a Redis counter
> would slot into.
>
> **The signing keys are not optional.** `config.py` raises at import if either
> `SECRET_KEY` or `JWT_SECRET_KEY` still holds the placeholder `.env.example`
> ships for it and `FLASK_DEBUG` is not `1`, because the failure it prevents is
> silent: a deployment signing its session cookies with a constant that is in
> this repository boots and serves exactly like a safe one, while anyone can
> forge a session and rewrite the catalogue. The two placeholders are different
> strings, so both are listed in `config.py`. `JWT_SECRET_KEY` inherits
> `SECRET_KEY` when unset and should be its own 32+ byte value.
>
> The session cookie is itself a credential — `api/security.py` accepts it in
> place of a bearer token — so it is `HttpOnly`, `SameSite=Lax`, and `Secure`
> outside debug.
>
> **A session-authenticated write also needs `X-Requested-With`.** The browser
> attaches the cookie to *any* request to this origin, including one made by a
> page belonging to somebody else, so accepting the cookie is what makes CSRF
> possible. A cross-site HTML form cannot set a header at all, and a cross-site
> `fetch()` that sets one asks for a preflight this API does not answer — so the
> header's presence is proof the request came from our own code. Its value is
> irrelevant. `core/api.js` sends it on every request, which is why no call site
> has to know about it.
>
> This mattered for the two upload endpoints. The JSON ones were incidentally
> safe (`Content-Type: application/json` needs a preflight of its own), but
> `multipart/form-data` is a content type a plain `<form>` can send, so
> `POST /products/<id>/images/upload` and `POST /collections/<id>/cover` were
> reachable from any page in a browser holding a dashboard session.
>
> Reads are exempt: a cross-site GET cannot be read back, and refusing one would
> only lock out a dashboard whose token went stale. A write with a valid bearer
> token is exempt too — an API client has no cookie to be used against it, and
> that keeps Swagger's Authorize button working from the same browser the owners
> have the dashboard open in.

### Conventions

**Pagination** — every list endpoint accepts `page` (1-based, default 1) and
`limit` (default 10, max 100), and wraps its rows alongside:

```json
{ "pagination": { "total": 42, "page": 2, "pages": 5, "limit": 10 } }
```

Non-numeric or non-positive values return `400`.

> **The front end mostly does not page — and says so when it cannot.** The
> dashboard works out its counts and filters from whole lists in the browser,
> because no endpoint computes pieces-per-type or filters on "has a photograph".
> That is deliberate at this size and wrong past 100 pieces, which is the API's
> own cap. So `core/api.js` compares `pagination.total` against what arrived and
> throws, naming the endpoint and both numbers, rather than rendering a count
> that is quietly short. A caller that means to page says `page` (the storefront
> grid does, nine at a time), and one that only wants `pagination.total` says
> `partial`.
>
> When that error shows up, the fix is server-side: a `has_photos` filter on the
> products list and an endpoint for pieces-per-lookup.

**Search** — list endpoints accept `q` for a case-insensitive substring match on
name.

**Status codes**

| Code | Meaning |
|---|---|
| `200` / `201` | Success |
| `400` | Missing/invalid body fields, bad pagination, or illegal type nesting |
| `401` | Wrong password, a username sent without one, or a missing/expired access token and no session |
| `403` | A session-authenticated write with no `X-Requested-With` header |
| `422` | Malformed token, or the wrong token type for the endpoint |
| `404` | The resource, or something it references, does not exist |
| `409` | Name (or variant) already taken |
| `429` | Five failed logins for this username inside fifteen minutes |

### Behaviour the schema does not show

- **`color_ids` is ordered.** The first colour is the primary one — it is what
  the storefront badge tints itself with. Duplicates are collapsed.
- **`Pequeno`, `Médio` and `Grande` are seeded** by `db/schema.sql`, ordered by
  `position` rather than by id. The list is the owners' to extend.
- **Variants, images and sizes are sub-resources**, not fields on the product
  body: `POST /products/<id>/variants`, `/images`, and `PUT /sizes`.
- **`PUT /products/<id>/sizes` replaces the whole list**; `{"size_ids": []}` puts
  a product back to its default size only.
- **Every image belongs to a colour set**, through its `variant_id`, which is
  required: a piece looks different in each colourway, so a photograph standing
  for the piece as a whole was always one colour's photo doing double duty.
  `primary_image` is the first photograph of the first colour that has one.
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

**Styling is [Bootstrap](https://getbootstrap.com/) 5.3.8**, vendored at
`static/bootstrap/`. `static/css/theme.css` retints it through its own
`--bs-*` custom properties — no Sass build — and `static/css/store.css` adds only
what Bootstrap does not ship: the gallery, the thumbnail rail and the grid tiles.

Bulma has been removed entirely. Layout is Bootstrap's own grid (`row` with
`col-*`, or `row-cols-*` where every cell behaves the same) rather than bespoke
CSS grid rules, and the navbar, offcanvas sidebar, dropdown, tabs, pagination and
modal parts are all the framework's. The one place we do not use its component is
the modal element itself: a native `<dialog>` wearing Bootstrap's `.modal-*`
classes, because the browser's top layer is what keeps a confirmation raised from
inside a dialog in front of it rather than behind its own backdrop.

FontAwesome, SweetAlert2 and PhotoSwipe remain, none of which depended on either
framework.

### Error pages

`errors/404.html` and `errors/500.html` extend the storefront base, so an error
still shows the navbar, footer and contact details. The handlers in `app.py`
check the request path: anything under `/api` gets a JSON body instead, so API
clients never receive HTML.

### Catalog

- Filters live in the sidebar: search, material, product type (with sub-types
  indented under their parent) and collection.
- Every applied filter renders as a navy pill reading `Group: Value ×`, with
  Bootstrap's `.btn-close` as the ×. Clicking the badge removes that filter; the
  sidebar and the badge row are two views of the same state.
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
app.py                  The entry point: builds the app, and nothing else
cli.py                  The flask commands: init-db, migrate, seed,
                        sweep-uploads, create-user
config.py               Config read from environment variables
uploads.py              Storing uploaded photographs on disk, and sweeping them
type_icons.py           Name -> Font Awesome class, the one copy of that table

api/                    The HTTP surface, and only that
  __init__.py           Api object; mounts every namespace under /api
  pagination.py         Request-arg parsing and the pagination envelope
  rate_limit.py         The sliding windows behind logins and storefront events
  security.py           auth_required — bearer token or session, on every write
  models/               flask-restx marshalling models — these ARE the Swagger docs
  routes/               HTTP concerns only: validation, status codes, marshalling
    crud.py             The route bodies they share: paging, 404, 409
    products/           One namespace, four modules: the product itself, its
                        variants, its photographs, its sizes

repositories/           Every SQL statement in the application, one class per table
  base.py               The reads the lookup tables share
db/
  __init__.py           PyMySQL connection handling and schema init
  migrate.py            The numbered-.sql runner behind `flask migrate`
  seed.py               The development catalogue behind `flask seed`
  schema.sql            Full schema, dropped and recreated by init-db
  migrations/           Numbered .sql files, each applied once, in order

web/                    Server-rendered storefront and dashboard blueprints
templates/  static/     Jinja templates and assets
docs/                   Written-down plans for work in progress
tests/                  pytest suite, isolated per test by truncating tables
```

### Layering rules

- **Routes never contain SQL.** They validate input, call repositories, and map
  outcomes to status codes.
- **Repositories never import Flask.** They take a MySQL cursor and return
  plain dicts, which makes them directly unit-testable.
- **`get_db_connection()` owns the transaction** — it commits on success and
  rolls back on exception, so handlers don't call `commit()` themselves.
- Cascades are implemented in the repositories **and** declared as foreign keys.
  The repositories are what runs; the constraints are the backstop. See *Storage
  model* above.
