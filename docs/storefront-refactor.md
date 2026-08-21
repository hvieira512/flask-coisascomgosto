# Storefront refactor

Bringing the three public pages to the prototype: the landing page, the catalogue
and a piece. The design decisions are settled — this is how they get built.

**The rule that shapes everything below: Bootstrap first.** Every layout, every
band, every card, every dark section is Bootstrap's own. Custom CSS is allowed
only where Bootstrap has no answer, and every survivor is listed by name in
"What custom CSS exists" — if it is not on that list it does not get written.

---

## Tokens

`static/css/theme.css`, which is the only place colour is decided.

| Token | Now | After | Why |
|---|---|---|---|
| `--ccg-paper` | `#FAF8F5` | `#FAF8F4` | a degree warmer |
| `--ccg-paper-deep` | `#F3EFE8` | `#F4EFE5` | the band under the hero reads gold-lit |
| `--ccg-line` | `#E7E1D7` | `#E4DAC6` | hairlines are the most repeated element on the page; warming them is what turns the whole shop gold |
| `--ccg-gold` | — | `#A67C2E` | sampled off the gold leaf. Small caps, rules, the chosen state |
| `--ccg-gold-lift` | — | `#C9A24E` | the same on a dark ground |
| `--ccg-pitch` | — | `#17161A` | the painted black boxes. One band, and one button |

Navy keeps its job — links and navigation — and the state colours are untouched.
Gold is not a second accent to spend freely: it marks *this one*, and the rule
above a section heading.

**The dark band is Bootstrap's, not ours.** `data-bs-theme="dark"` on a section
flips every Bootstrap variable inside it, so the contacts band needs no colours of
its own. theme.css gains one `[data-bs-theme="dark"]` block defining the pitch
palette, and after that `bg-body`, `text-body-secondary`, `border-top` and
`btn-outline-light` all behave inside it with no help.

---

## What custom CSS exists

Everything else in `store.css` that these pages use is deleted.

**Kept, unchanged:** `.section` (vertical rhythm for a band), `.eyebrow`,
`.measure`, `.icon`, `.disc`, `.fs-7`, the display-serif rule on `h1, h2`, the
timeline, the gallery stage and its arrows, the lightbox.

**Added — six rules, and the reason each cannot be a utility:**

| Class | Why not Bootstrap |
|---|---|
| `.hero-wash` | a radial gradient. Bootstrap has `bg-gradient`, which is a fixed white overlay |
| `.mark` | the 2px gold rule above a heading, as `::before`. A signature element, not a utility |
| `.text-gold` | `text-*` is a closed set in Bootstrap and gold is not in it |
| `.tile-scrim` | the gradient that makes a name legible over a photograph. `card-img-overlay` positions it; nothing tints it |
| `.swatch-dot` | a two-tone circle built from two colours. Composed in JS today, and stays there |
| `.photo-cover` | `object-fit: cover` on an `<img>`. Bootstrap has no object-fit utility |

**Deleted:** `.type-card`, `.type-card-media`, `.type-card-icon`,
`.collection-strip` and its card, `.filters-panel`, `.craft-step`,
`.hero-scroll*` (replaced by `.mark`-styled markup + Bootstrap position
utilities), `#contacts .card`, `.store-footer`, `.media-photo`.

---

## The landing page

`templates/store/home.html`

**1 · Hero** — unchanged in structure, which is the point: Hugo's centred hero
stays. `min-vh-100` less the navbar, `d-flex align-items-center text-center`, the
headline at `display-5` (3rem — *not* larger), the lede at `fs-5`. What changes is
the light: `.hero-wash` puts a gold radial behind it where a blue one used to be,
the eyebrow is `.text-gold`, and the scroll cue's disc is a gold hairline. No
photograph, no button.

**2 · Origem** — the rhythm break, and the one section that stops looking like the
others. A full-bleed `<section data-bs-theme="dark">` with the makers photograph as
a `background-image`, the story over it in a `container` + `col-lg-7`, and a
bottom-up scrim so the text sits under their faces rather than across them. The
photograph is served at 4:3 — a wide letterbox crop of a square photograph is what
made them look squashed.

**3 · O ofício** — `row row-cols-1 row-cols-md-3 g-4`, each step a `col` with
`border-top`. The numeral becomes `display-4 .text-gold` in the display serif
instead of an 11px eyebrow: it is a sequence, and the size is what makes it read
as one.

**4 · As peças** — `row row-cols-2 row-cols-md-3 row-cols-lg-4 g-2`. Each family
is `<a class="card border-0">` holding a Bootstrap `ratio` box with the photograph
and a `card-img-overlay` carrying the name in the display serif over
`.tile-scrim`. The description moves off the tile. A family with no photograph
keeps `bg-body-secondary` and its name in the serif — no icon disc, no grey box.
"Ver tudo" stays, as the one tile with a border and no photograph.

**5 · Percurso** — the existing timeline component, restyled: gold marker, gold
date, no card. Its drag-and-arrows behaviour is already built and is reused as-is
for the catalogue's collections.

**6 · Contactos** — `data-bs-theme="dark"` closes the page. The address in the
display serif at `fs-4`, then a `dl` of four labelled links with `border-top` on
each row. Replaces five cards and five icon discs. The footer joins the same band.

---

## The catalogue

`templates/store/products.html`

- **Header** — `Catálogo` at `display-6`, the count on the right, and the
  "preços sob consulta" line on **one** line: no `.measure`, `fs-6`.
- **Collections** — a rail across the full width, above both columns, showing
  *every* collection. Few grow to fill the row (`flex: 1 0 14rem`); many keep
  their width and the rail scrolls — dragged with the mouse, or walked with the
  arrows that appear on hover and exist only when there is somewhere to go. This
  is `timeline.js` generalised, not a second implementation. No "Ver tudo" tile:
  the grid below is already everything.
- **Filters** — `col-lg-3`, no panel box. A search field with a bottom rule only
  (`form-control` + `border-0 border-bottom rounded-0`), then each facet as a
  label over `border-bottom` and rows of `form-check` with the count in
  `font-monospace text-body-tertiary ms-auto`.
- **Grid** — `col-lg-9`, `row row-cols-2 row-cols-lg-3 g-4`. Each piece: a
  `ratio` box at 4:5, then the name and its type on a line with `border-top`, then
  the colourways as `.swatch-dot`s. **`align-content-start` on the card** — a grid
  item is stretched to its row's height and distributes the extra into its
  implicit rows, which is why two-line names made every photograph in that row
  taller. The name line reserves two lines so the swatches align across the row.

---

## A piece

`templates/store/product.html`

The layout Hugo asked for: the photograph and the facts the same height, the
photograph never stretched.

- `col-lg-7` for the gallery, `col-lg-5` for the facts.
- **The thumbnails run down the left of the stage** from `lg` up
  (`flex-column`), and along the bottom below `lg` (`flex-row`) — a column costs
  width, which the desktop has, and the strip cost height, which is what forced
  the crop.
- The stage keeps its `ratio` at 4:5 and its own aspect. It is *not* stretched to
  match the column: at that width a 4:5 crop becomes a letterbox and the piece
  turns into a fragment of itself. The proportions are chosen so that the stage
  and the facts come out the same height on their own.
- The gallery keeps everything it already has — arrows, counter, zoom, lightbox,
  keyboard.
- Colourways become `.swatch-dot`s with the chosen one named underneath, instead
  of four tinted pills in front of the photograph. Sizes stay as buttons.
- The description opens the block of facts, above the specification rows.
- `Pedir informações` is `btn-lg w-100` on the pitch ground.

---

## Responsive

One decision per breakpoint, and every one of them is a Bootstrap prefix.

| | `< sm` (phone) | `md` | `lg` and up |
|---|---|---|---|
| Navbar | collapsed, Bootstrap's own toggle | collapsed | one line, links right |
| Hero | `display-5` scales down; cue kept | — | full height |
| Origem | 60vh, scrim heavier | 70vh | 86vh, text at `col-lg-7` |
| O ofício | stacked, 1 col | 3 cols | 3 cols |
| As peças | 2 cols | 3 cols | 4 cols |
| Contactos | stacked | stacked | 2 cols |
| Catálogo grid | 2 cols | 2 cols | 3 cols |
| Filtros | above the grid, full width | above | `col-lg-3` beside it |
| Colecções rail | 2 visible, dragged | 3 visible | all, or dragged |
| Peça | stage full width, thumbs in a row underneath | same | thumbs in a column at the left |

Nothing has a horizontal scrollbar at 390px; the rail scrolls inside itself.

---

## Order of work

One commit per step. `pytest` and `env/bin/pyright` green at each, and each step
looked at in the browser at 1280 and 390 before it is committed.

1. Tokens, the dark-theme block, the grain, and the six new rules.
2. Navbar and footer.
3. The landing page.
4. The catalogue, and the rail generalised out of the timeline.
5. The piece.
6. Delete the CSS the four steps above orphaned, and recapture the appearance
   baselines.

## Verification

- `pytest` — 893 green now. The browser tests assert on ids and behaviour rather
  than classes, so most should survive; anything that asserts on a deleted class
  is updated with its reason stated in the commit.
- `env/bin/pyright` — 0 errors.
- Every page at 1280 and 390, in the running app, against the prototype.
- `SCREENSHOTS=update` then `SCREENSHOTS=1` on the appearance suite, last.
- The tracking still records: a view, an enquiry with its colour, a search, a
  filter. The refactor touches the markup those listeners hang off.
