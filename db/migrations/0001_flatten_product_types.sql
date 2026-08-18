-- Product types are flat: the type is the family ("Caixa") and the shape lives in
-- the piece's own name ("Caixa rectangular"). Every parent that had children held
-- no pieces of its own, so the level was a folder rather than a fact.
--
-- Pieces move up to their parent BEFORE the sub-types go, or they would lose the
-- one column that is NOT NULL.
UPDATE products p
    JOIN product_types t ON p.type_id = t.id
   SET p.type_id = t.parent_id
 WHERE t.parent_id IS NOT NULL;

DELETE FROM product_types WHERE parent_id IS NOT NULL;

-- parent_key was a generated column that folded NULL to 0, so that the unique
-- key could constrain top-level names too. With no hierarchy, name is unique on
-- its own.
ALTER TABLE product_types DROP INDEX uq_product_types_parent_name;
ALTER TABLE product_types DROP INDEX idx_product_types_parent;
ALTER TABLE product_types DROP COLUMN parent_key;
ALTER TABLE product_types DROP COLUMN parent_id;
ALTER TABLE product_types ADD UNIQUE KEY (name);
