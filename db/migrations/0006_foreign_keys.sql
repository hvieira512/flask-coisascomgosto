-- Foreign keys, as a backstop rather than a change of behaviour.
--
-- The schema has had none, and the repositories do the work instead: deleting a
-- collection detaches its products and colour sets, deleting a colour set
-- removes the variants using it, deleting a product removes its variants, sizes
-- and photographs. That is careful code, and it has held — there is not one
-- orphan row in the live database. But it is correctness that depends on every
-- delete going through the right method, and one direct DELETE anywhere leaves
-- orphans behind with nothing to notice.
--
-- Every rule below is the behaviour a repository already implements, so this
-- changes nothing about how the app behaves; it moves the guarantee from the
-- code into the database. The repositories keep their delete methods regardless:
-- they return the URLs of the photographs they removed so the routes can delete
-- the files, and a cascade cannot do that.
--
-- RESTRICT on products.type_id is the exception worth naming. type_id is NOT
-- NULL — there is no "unfiled piece" state — so a type in use must not be
-- deletable. routes/product_types.py already answers 409 with the count of
-- pieces still using it, which is the message the owners should see; this only
-- stops the same thing happening behind the API's back.

ALTER TABLE products
    ADD CONSTRAINT fk_products_type
        FOREIGN KEY (type_id) REFERENCES product_types (id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_products_material
        FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_products_collection
        FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_products_default_size
        FOREIGN KEY (default_size_id) REFERENCES sizes (id) ON DELETE SET NULL;

ALTER TABLE color_sets
    ADD CONSTRAINT fk_color_sets_collection
        FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE SET NULL;

ALTER TABLE color_set_colors
    ADD CONSTRAINT fk_color_set_colors_set
        FOREIGN KEY (color_set_id) REFERENCES color_sets (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_color_set_colors_color
        FOREIGN KEY (color_id) REFERENCES colors (id) ON DELETE CASCADE;

ALTER TABLE product_variants
    ADD CONSTRAINT fk_product_variants_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_product_variants_color_set
        FOREIGN KEY (color_set_id) REFERENCES color_sets (id) ON DELETE CASCADE;

ALTER TABLE product_images
    ADD CONSTRAINT fk_product_images_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_product_images_variant
        FOREIGN KEY (variant_id) REFERENCES product_variants (id) ON DELETE CASCADE;

ALTER TABLE product_sizes
    ADD CONSTRAINT fk_product_sizes_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_product_sizes_size
        FOREIGN KEY (size_id) REFERENCES sizes (id) ON DELETE CASCADE;
