-- A piece does not belong to a collection. Its colours do.
--
-- `products.collection_id` said otherwise, and said it in parallel with the real
-- relationship: 0009 made a colour set belong to many collections, and a piece is
-- offered in colour sets, so "which collections is this piece in" already had an
-- answer — collection -> colour set -> variant -> piece. The column was a second,
-- unsynchronised answer to the same question, and the two disagreed for four of
-- the six collections in the live catalogue when this ran:
--
--     Filigrana         column 9    colours 13
--     Bordados          column 2    colours 13
--     Lenços            column 1    colours  1
--     Azul e Preto      column 0    colours  0
--     Branco e Dourado  column 0    colours  9
--     Barra da Saia     column 0    colours  0
--
-- The shop showed the consequence: the collections rail read "Branco e Dourado ·
-- ainda sem peças" beside a collection that reaches nine of the fourteen.
--
-- Nothing is migrated into anything: the colours already carry it. Checked before
-- dropping — no piece named a collection in this column that its colour sets do
-- not also reach, so no piece comes out of this with fewer collections than it
-- had.
--
-- What this does lose is the ability to say "this piece is in that collection"
-- without saying which of its colours puts it there. That is the point: if a
-- piece belongs somewhere, one of its colourways is why.

ALTER TABLE products
    DROP FOREIGN KEY fk_products_collection;

ALTER TABLE products
    DROP KEY idx_products_collection,
    DROP COLUMN collection_id;
