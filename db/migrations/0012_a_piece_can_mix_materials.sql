-- A piece is made of one material, or of several.
--
-- `products.material_id` was a single nullable column, and the comment on it read
-- "material_id is not [required] — a piece may mix materials, or predate the
-- list". So the column used NULL for two different facts: "we never classified
-- this" and "it is made of more than one thing". The second is the one that
-- matters — Manel e Maria is a wooden base with a figure of modelling paste, and
-- the catalogue could only call it Madeira or nothing.
--
-- The relationship is therefore a join, the same one product_sizes already is.
--
-- No position column: the materials of a piece are not in an order, and nothing
-- would read it. There is no "main" material either — a base and a figure are
-- both what the piece is made of.
--
-- Both sides CASCADE. Deleting a material takes it off the pieces made of it,
-- which is what the dashboard has always warned that it does; before this it was
-- ON DELETE SET NULL on the column, which meant the same thing.

CREATE TABLE product_materials (
    product_id INT NOT NULL,
    material_id INT NOT NULL,
    PRIMARY KEY (product_id, material_id),
    KEY idx_product_materials_material (material_id),
    CONSTRAINT fk_product_materials_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    CONSTRAINT fk_product_materials_material
        FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO product_materials (product_id, material_id)
SELECT id, material_id FROM products WHERE material_id IS NOT NULL;

ALTER TABLE products
    DROP FOREIGN KEY fk_products_material;

ALTER TABLE products
    DROP KEY idx_products_material,
    DROP COLUMN material_id;
