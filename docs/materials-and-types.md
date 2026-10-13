# A piece can mix materials, and the Tipos page says so

## Why

`products.material_id` is one nullable column, and the schema's own comment
admits the problem while drawing the wrong conclusion: it says the column is
nullable because "a piece may mix materials" — using NULL to mean "several",
which loses the fact instead of storing it. Manel e Maria is a wooden base and a
figure of modelling paste; today the catalogue can only say "Madeira", or nothing.

The dashboard's Tipos page also under-uses what it has: seven types drawn as
Font Awesome discs, a description column, and a materials list that shows names
with no idea how many pieces are made of each.

## What changes

### 1. `product_materials` (migration 0012)

The same shape as `product_sizes`, and the same shape 0009 gave the colour sets:

```sql
CREATE TABLE product_materials (
    product_id INT NOT NULL,
    material_id INT NOT NULL,
    PRIMARY KEY (product_id, material_id),
    KEY idx_product_materials_material (material_id),
    ... ON DELETE CASCADE on both sides
);
INSERT INTO product_materials SELECT id, material_id FROM products
 WHERE material_id IS NOT NULL;
ALTER TABLE products DROP ... material_id;
```

No `position` column: the two materials of a piece are not ordered, and a column
nobody reads is a column somebody later has to explain. Both sides CASCADE —
deleting a material takes it off the pieces, which is what the dashboard already
warns it does.

Both halves, as the Flask app needed them then: `db/schema.sql` **and** the
migration file. (The Laravel app has one migration and no separate schema.)

### 2. Reads and writes

`ProductRepository` loses the `materials` LEFT JOIN and gains `get_materials`,
`set_materials` and `_attach_materials` — copied from the sizes trio above them,
because it is the same join table with a different name. Filtering by material
becomes `EXISTS` against the join; the material facet counts from it, so a piece
with two materials counts under both.

The API's product grows `materials` (a list) in place of `material`, and takes
`material_ids` on create and update — beside `size_ids`' precedent, but in the
piece's own payload the way a colour set takes `collection_ids`, so saving a
piece is still one request. An unknown id is a 404, via `missing_ids`.

### 3. The photograph a type shows

Nothing new: `ProductTypeRepository.cover_images` already answers this for the
shop's family tiles, and `product_counts` already counts the pieces. `list` and
`get` wrap the base's to attach both, so `/api/product-types/` carries `image` and
`pieces` and the dashboard reads the same numbers the shop does.

That leaves two ways of borrowing a photograph in the codebase — this batch one,
and the correlated subquery in `CollectionRepository.COLUMNS`. Deliberate: the
join paths differ (type → piece → photograph against collection → colour set →
variant → photograph), the type's batch query predates this work and is used by a
server-rendered page, and a shared helper would have to be parameterised by join
path to serve both, which is more indirection than the repetition costs.

### 4. The pages

**Tipos** (`/dashboard/types`), matching the prototype's information design:
photograph, name and description, the icon shown as what it is — the drawing the
shop uses while a piece has no photograph — and the piece count. Beside it, the
materials panel: each material with how many pieces are made of it, "nenhuma"
marked when none are, and the line that explains why the numbers can add to more
than the catalogue.

Counts come from `/api/products/facets`, which is already server-side, instead of
`counts.js` fetching every product to count them in the browser — that read is
capped at 100 products and this page would have quietly stopped being true.

**The piece's form**: the material `<select>` becomes the same multi-select chips
the colour-set form uses for its collections, with the note that most pieces have
one material.

That widget existed twice by the end, so it is now one module —
`js/dashboard/picks.js`: the chip, the toggle, and reading the answer back. The
colour-set form kept a `Set` in step with its chips; it no longer does, because
the chips already know. `.collection-chip` became `.pick-chip`, since it stopped
being about collections the moment a material wore it.

**The shop**: the spec block says "Material" or "Materiais" and lists them.

## Verification

- Migration against the dev database, then `flask migrate --status` (now
  `php artisan migrate:status`).
- Tests: the join replaces the column (create, update, replace, none), the facet
  counts both materials of a piece, the filter finds a piece under either, an
  unknown material is 404, and a deleted material leaves the piece.
- Browser: Manel e Maria saved with two materials shows both in the shop's spec
  block and appears under both filters; the Tipos page shows seven photographs,
  the counts, and the empty-material state.
- The test suite (then `pytest` and `pyright`, now `vendor/bin/pest`) and the
  appearance suite; recapture what the new pages change.

## Not doing

- No parts or components level: two materials of one piece, not two objects.
- No ordering of materials, no "primary" material.
- ~~`products.collection_id` stays as it is~~ — done next, in 0013: the column
  is gone and a collection reaches a piece through the piece's colour sets.
