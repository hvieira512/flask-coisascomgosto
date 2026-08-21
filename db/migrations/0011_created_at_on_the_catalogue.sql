-- When a catalogue row was added.
--
-- Nothing in the catalogue has ever recorded this, so the dashboard cannot say
-- "three pieces added this month" about the shop's own history — only about
-- whatever happens from here. The column costs nothing to carry and cannot be
-- added retroactively, which is the whole reason it goes in now.
--
-- EXISTING ROWS TAKE THE DATE THIS MIGRATION RAN, AND THAT IS NOT WHEN THEY WERE
-- ADDED. The real dates are gone. Nobody should read the first fourteen pieces as
-- a launch week, and nothing in the application may count a window that begins
-- before this migration: `repositories/analytics.py` asks
-- `schema_migrations.applied_at` for this file's own row and says nothing rather
-- than "fourteen new pieces", because an invented number is worse than a gap.
--
-- Five ALTERs in one file, against migrate.py's own note about DDL committing
-- implicitly: this is one logical change, and splitting it into five files to
-- guard against a half-applied ADD COLUMN would be five files for a failure whose
-- symptom is "column already exists" and whose fix is running the rest by hand.
ALTER TABLE products
    ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE product_variants
    ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE product_images
    ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE collections
    ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE color_sets
    ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Only products is read so far, and only ever as a count over a window.
CREATE INDEX idx_products_created ON products (created_at);
