-- CoisasComGosto catalog schema (MySQL 8).
--
-- Domain shape:
--   category            a product's taxonomy bucket (required, e.g. "Madeira")
--   product type        what the object is (hairbrush, picture frame, wooden box).
--                       Types nest exactly one level: a "Coracao" type can have
--                       sub-types for how it is finished, e.g. "with string to
--                       hang" vs "base for mini figures".
--   collection          a themed grouping (e.g. "Barra da Saia") that owns colour sets
--   colour              a single named colour, optionally with a hex swatch
--   colour set          a named combination of colours ("White and Green"), normally
--                       belonging to a collection
--   product variant     a product offered in one specific colour set
--   size                S / M / L; a product may declare a default size and/or a set
--                       of sizes it is available in
--   product image       a photo. Attached to a variant when the colour set
--                       changes how the item looks, or to the product itself as
--                       a fallback shown when a variant has no photos of its own.
--   contacts            the shop's own details, shown in the footer and on the
--                       landing page. A single row, edited rather than added to.
--   event               a fair, market or show the workshop took part in. Drives
--                       the timeline on the landing page.
--
-- NOTE ON REFERENTIAL INTEGRITY
-- This schema is deliberately non-relational: there are no FOREIGN KEY
-- constraints. Relationships are plain integer columns backed by indexes, and
-- every cascade or orphan-cleanup is performed in the repository layer instead
-- of by the database. That means MySQL will NOT stop an orphan row being
-- written by anything that bypasses api/repositories/.
--
-- NOTE ON COLUMN TYPES
-- Text columns that are indexed, unique, or part of a composite key must be
-- VARCHAR: MySQL cannot index a TEXT column without a prefix length. Free prose
-- that is never searched by equality stays TEXT.
--
-- NOTE ON NULLS IN UNIQUE KEYS
-- MySQL treats NULLs as distinct inside a UNIQUE index, so
-- UNIQUE (parent_id, name) does NOT stop two top-level types sharing a name.
-- That gap is closed in ProductTypeRepository.name_exists, which compares with
-- the null-safe <=> operator.
--
-- Dropped children-first so a re-run is always clean.
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS product_images;
DROP TABLE IF EXISTS product_sizes;
DROP TABLE IF EXISTS product_variants;
DROP TABLE IF EXISTS color_set_colors;
DROP TABLE IF EXISTS color_sets;
DROP TABLE IF EXISTS colors;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS product_types;
DROP TABLE IF EXISTS sizes;
DROP TABLE IF EXISTS collections;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- A themed grouping of products, e.g. "Barra da Saia".
CREATE TABLE collections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- A single colour. `hex` is optional and drives swatches in the dashboard.
CREATE TABLE colors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    hex VARCHAR(9)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- S / M / L. `position` controls display order rather than relying on the name.
CREATE TABLE sizes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(40) NOT NULL UNIQUE,
    position INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- What the object is: "Hairbrush", "Picture frame", "Wooden box", "Coracao".
-- parent_id nests sub-types exactly one level deep. The one-level rule is
-- enforced by ProductTypeRepository.
CREATE TABLE product_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    parent_id INT,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    -- Font Awesome class (e.g. 'fa-heart') drawn on products that have no
    -- photo yet. Null falls back to a keyword guess from the type name.
    icon VARCHAR(60),
    UNIQUE KEY uq_product_types_parent_name (parent_id, name),
    KEY idx_product_types_parent (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- A named combination of colours, e.g. "White and Green".
-- collection_id is nullable: a set normally belongs to a collection, but a
-- standalone set is allowed.
CREATE TABLE color_sets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    collection_id INT,
    name VARCHAR(120) NOT NULL,
    UNIQUE KEY uq_color_sets_collection_name (collection_id, name),
    KEY idx_color_sets_collection (collection_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Which colours make up a set, and in what order.
CREATE TABLE color_set_colors (
    color_set_id INT NOT NULL,
    color_id INT NOT NULL,
    position INT NOT NULL DEFAULT 0,
    PRIMARY KEY (color_set_id, color_id),
    KEY idx_color_set_colors_color (color_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    type_id INT,
    collection_id INT,
    default_size_id INT,
    name VARCHAR(180) NOT NULL,
    description TEXT,
    KEY idx_products_category (category_id),
    KEY idx_products_type (type_id),
    KEY idx_products_collection (collection_id),
    KEY idx_products_default_size (default_size_id),
    KEY idx_products_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One product offered in one colour set. The unique constraint stops the same
-- colour set being attached to a product twice.
CREATE TABLE product_variants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    color_set_id INT NOT NULL,
    UNIQUE KEY uq_product_variants_product_color_set (product_id, color_set_id),
    KEY idx_product_variants_product (product_id),
    KEY idx_product_variants_color_set (color_set_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Photos of a product. variant_id NULL means the image belongs to the product
-- as a whole and is used as the fallback for variants with no photos of their
-- own; a non-null variant_id ties the photo to one colour set.
CREATE TABLE product_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    variant_id INT,
    url VARCHAR(500) NOT NULL,
    alt VARCHAR(255),
    position INT NOT NULL DEFAULT 0,
    KEY idx_product_images_product (product_id),
    KEY idx_product_images_variant (variant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- The sizes a product is available in. Empty means "only the default size".
CREATE TABLE product_sizes (
    product_id INT NOT NULL,
    size_id INT NOT NULL,
    PRIMARY KEY (product_id, size_id),
    KEY idx_product_sizes_size (size_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(190) NOT NULL UNIQUE,
    -- Werkzeug scrypt hashes run to ~162 chars; 255 leaves room for a change
    -- of hashing method without a migration.
    password VARCHAR(255) NOT NULL,
    is_admin TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- The shop's contact details. This is a singleton: exactly one row, always id 1,
-- updated in place. There is deliberately no separate phone column — the
-- WhatsApp number is the phone number, and the site links it as wa.me/<number>.
CREATE TABLE contacts (
    id INT PRIMARY KEY,
    address VARCHAR(255),
    email VARCHAR(190),
    whatsapp VARCHAR(40),
    -- Where the address opens. A short maps.app.goo.gl link is preferred: the
    -- long /maps/place/ form carries a session token that eventually rots.
    maps_url VARCHAR(500),
    facebook_url VARCHAR(500),
    instagram_url VARCHAR(500),
    CONSTRAINT chk_contacts_singleton CHECK (id = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Fairs, markets and shows the workshop has taken part in.
-- `ends_on` is optional: a one-day market only has a start.
CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(180) NOT NULL,
    location VARCHAR(180),
    description TEXT,
    starts_on DATE NOT NULL,
    ends_on DATE,
    url VARCHAR(500),
    -- The timeline reads newest-first, so the sort column is indexed.
    KEY idx_events_starts_on (starts_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- The standard size run. Seeded so the API is usable immediately.
INSERT INTO sizes (name, position) VALUES ('S', 1), ('M', 2), ('L', 3);

-- Seeded from the links already used across the site.
INSERT INTO contacts (id, address, email, whatsapp, maps_url, facebook_url,
                      instagram_url)
VALUES (
    1,
    'Viana do Castelo, Portugal',
    'geral@coisascomgosto.pt',
    '939320334',
    'https://maps.app.goo.gl/bAYkhcE3gvaKDw5W9',
    'https://www.facebook.com/coisascomgosto.vianadocastelo/',
    'https://www.instagram.com/coisascomgostovc/'
);
