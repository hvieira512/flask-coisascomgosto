-- S / M / L is clothing vocabulary on a shop selling wooden boxes; the rest of
-- the storefront speaks Portuguese.
--
-- By name, and only where the old name is still there, so running this against a
-- database somebody already renamed by hand changes nothing. product_sizes and
-- products.default_size_id reference sizes by id, so no link is disturbed.
UPDATE sizes SET name = 'Pequeno' WHERE name = 'S';
UPDATE sizes SET name = 'Médio' WHERE name = 'M';
UPDATE sizes SET name = 'Grande' WHERE name = 'L';
