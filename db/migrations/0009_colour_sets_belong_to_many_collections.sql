-- A colour set belongs to many collections, or to none.
--
-- It had one nullable `collection_id`, so choosing a collection for a set was
-- compulsory-ish and exclusive: "Preto e Branco" could be Filigrana's or
-- Bordados' but not both, and using the same combination in a second collection
-- meant creating it twice under some other name. The set is a thing in its own
-- right — the same two colours are the same two colours whichever collection
-- shows them — so the relationship is a join table.
--
-- Two consequences worth naming:
--
-- The name becomes unique across the whole table rather than within a collection.
-- That is the point: one combination, named once. Nothing had to be merged for
-- it — no name was in use twice when this ran — though "Azul e Branco"
-- (Filigrana) and "Branco e Azul" (Bordados) are the same pair spelled two ways,
-- which is the duplication the old shape encouraged. They are left alone here;
-- merging them is a decision about the catalogue, not about the schema.
--
-- A collection that is deleted now loses its links rather than orphaning its
-- sets, which is what ON DELETE CASCADE on the join means. The sets themselves
-- survive, as they did before.

CREATE TABLE collection_color_sets (
    collection_id INT NOT NULL,
    color_set_id INT NOT NULL,
    PRIMARY KEY (collection_id, color_set_id),
    KEY idx_collection_color_sets_set (color_set_id),
    CONSTRAINT fk_collection_color_sets_collection
        FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE,
    CONSTRAINT fk_collection_color_sets_set
        FOREIGN KEY (color_set_id) REFERENCES color_sets (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO collection_color_sets (collection_id, color_set_id)
SELECT collection_id, id FROM color_sets WHERE collection_id IS NOT NULL;

ALTER TABLE color_sets
    DROP FOREIGN KEY fk_color_sets_collection;

ALTER TABLE color_sets
    DROP KEY uq_color_sets_collection_name,
    DROP KEY idx_color_sets_collection,
    DROP COLUMN collection_id,
    ADD UNIQUE KEY uq_color_sets_name (name);
