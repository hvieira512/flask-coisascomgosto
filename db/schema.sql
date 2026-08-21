-- CoisasComGosto catalog schema (MySQL 8).
--
-- Domain shape:
--   product type        the family a piece belongs to ("Caixa", "Coração",
--                       "Moldura"). Required: it is the one fact every piece has.
--                       Flat — the shape lives in the product's own name.
--   material            what it is made of ("Madeira", "Tecido"). Optional, and
--                       a lookup the owners maintain themselves.
--   collection          a themed grouping (e.g. "Barra da Saia") that owns colour sets
--   colour              a single named colour, optionally with a hex swatch
--   colour set          a named combination of colours ("White and Green"), normally
--                       belonging to a collection
--   product variant     a product offered in one specific colour set
--   size                Pequeno / Médio / Grande; a product may declare a default
--                       size and/or a set of sizes it is available in
--   product image       a photo, of one variant. Every photograph belongs to a
--                       colour set, because the piece looks different in each.
--   contacts            the shop's own details, shown in the footer and on the
--                       landing page. A single row, edited rather than added to.
--   event               a fair, market or show the workshop took part in. Drives
--                       the timeline on the landing page.
--
-- NOTE ON REFERENTIAL INTEGRITY
-- The cascades are written twice, on purpose. Every FOREIGN KEY below states
-- what the repository layer already does — detach a product from a deleted
-- material, remove the variants of a deleted colour set, refuse to delete a type
-- still in use — and the repositories keep doing it, because they also return
-- the URLs of the photographs whose rows have gone so the routes can delete the
-- files. A cascade cannot do that.
--
-- So the repositories are the behaviour and the constraints are the backstop:
-- one direct DELETE that bypasses repositories/ no longer leaves orphans, it
-- fails or cascades correctly. The rules were added in 0006 against a database
-- with no orphan rows in it, which is the evidence the two agree.
--
-- NOTE ON COLUMN TYPES
-- Text columns that are indexed, unique, or part of a composite key must be
-- VARCHAR: MySQL cannot index a TEXT column without a prefix length. Free prose
-- that is never searched by equality stays TEXT.
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
DROP TABLE IF EXISTS materials;
DROP TABLE IF EXISTS users;
-- Not created below, and not part of this schema. It is dropped here because
-- init-db only removes what it names, which is how a table nothing referenced
-- survived in the live database until 0005.
DROP TABLE IF EXISTS categories;

-- What a piece is made of: "Madeira", "Tecido". A lookup the owners maintain
-- themselves, and optional on a product — a piece that mixes materials, or one
-- nobody has classified yet, simply has none.
CREATE TABLE materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- A themed grouping of products, e.g. "Barra da Saia".
-- image_url is the photograph that stands for the collection on the catalogue,
-- chosen by the owners rather than picked automatically from the pieces: the
-- collection is what they want a shopper to choose first, so which photograph
-- speaks for it is an editorial decision, not the first row of a query.
CREATE TABLE collections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT,
    image_url VARCHAR(500)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- A single colour. `hex` is optional and drives swatches in the dashboard.
CREATE TABLE colors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    hex VARCHAR(9)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Pequeno / Médio / Grande, in the owners' own words rather than clothing
-- letters. `position` controls display order rather than relying on the name.
CREATE TABLE sizes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(40) NOT NULL UNIQUE,
    position INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- The family a piece belongs to: "Caixa", "Coração", "Moldura". Flat by
-- design — the shape lives in the product's own name ("Caixa rectangular",
-- "Caixa de Joias"), so there is no level between the family and the piece.
CREATE TABLE product_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT,
    -- Font Awesome class (e.g. 'fa-heart') drawn on products that have no
    -- photo yet. Null falls back to a keyword guess from the type name.
    icon VARCHAR(60)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- A named combination of colours, e.g. "White and Green".
-- collection_id is nullable: a set normally belongs to a collection, but a
-- standalone set is allowed.
CREATE TABLE color_sets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    collection_id INT,
    name VARCHAR(120) NOT NULL,
    UNIQUE KEY uq_color_sets_collection_name (collection_id, name),
    KEY idx_color_sets_collection (collection_id),
    CONSTRAINT fk_color_sets_collection
        FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Which colours make up a set, and in what order.
CREATE TABLE color_set_colors (
    color_set_id INT NOT NULL,
    color_id INT NOT NULL,
    position INT NOT NULL DEFAULT 0,
    PRIMARY KEY (color_set_id, color_id),
    KEY idx_color_set_colors_color (color_id),
    CONSTRAINT fk_color_set_colors_set
        FOREIGN KEY (color_set_id) REFERENCES color_sets (id) ON DELETE CASCADE,
    CONSTRAINT fk_color_set_colors_color
        FOREIGN KEY (color_id) REFERENCES colors (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- type_id is required: what the object is, is the one fact every piece has.
-- material_id is not — a piece may mix materials, or predate the list.
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type_id INT NOT NULL,
    material_id INT,
    collection_id INT,
    default_size_id INT,
    name VARCHAR(180) NOT NULL,
    description TEXT,
    KEY idx_products_material (material_id),
    KEY idx_products_type (type_id),
    KEY idx_products_collection (collection_id),
    KEY idx_products_default_size (default_size_id),
    KEY idx_products_name (name),
    -- RESTRICT, not SET NULL: type_id is NOT NULL, so there is no unfiled state
    -- to fall back on. routes/product_types.py answers 409 with the number of
    -- pieces still using the type; this is the same refusal, one layer down.
    CONSTRAINT fk_products_type
        FOREIGN KEY (type_id) REFERENCES product_types (id) ON DELETE RESTRICT,
    CONSTRAINT fk_products_material
        FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE SET NULL,
    CONSTRAINT fk_products_collection
        FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE SET NULL,
    CONSTRAINT fk_products_default_size
        FOREIGN KEY (default_size_id) REFERENCES sizes (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One product offered in one colour set. The unique constraint stops the same
-- colour set being attached to a product twice.
CREATE TABLE product_variants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    color_set_id INT NOT NULL,
    UNIQUE KEY uq_product_variants_product_color_set (product_id, color_set_id),
    KEY idx_product_variants_product (product_id),
    KEY idx_product_variants_color_set (color_set_id),
    CONSTRAINT fk_product_variants_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    CONSTRAINT fk_product_variants_color_set
        FOREIGN KEY (color_set_id) REFERENCES color_sets (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Photos of a product, each belonging to one of its colour sets.
--
-- variant_id was nullable until 0007, where NULL meant "of the piece as a whole"
-- and stood in for any colour with no photograph of its own. A piece looks
-- different in each colourway, so that fallback showed the wrong thing — and,
-- being preferred by primary_image, it decided which tile the catalogue listed.
CREATE TABLE product_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    variant_id INT NOT NULL,
    url VARCHAR(500) NOT NULL,
    alt VARCHAR(255),
    position INT NOT NULL DEFAULT 0,
    -- Removing a photograph marks it and leaves the file alone; every read
    -- filters on this. The owners' only copy of a photograph may be the one they
    -- uploaded, so a mis-tap has to be an UPDATE and not a lost file.
    -- uploads.sweep() is the only thing that deletes either.
    deleted_at DATETIME NULL,
    KEY idx_product_images_product (product_id),
    KEY idx_product_images_variant (variant_id),
    KEY idx_product_images_deleted (deleted_at),
    CONSTRAINT fk_product_images_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    CONSTRAINT fk_product_images_variant
        FOREIGN KEY (variant_id) REFERENCES product_variants (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- The sizes a product is available in. Empty means "only the default size".
CREATE TABLE product_sizes (
    product_id INT NOT NULL,
    size_id INT NOT NULL,
    PRIMARY KEY (product_id, size_id),
    KEY idx_product_sizes_size (size_id),
    CONSTRAINT fk_product_sizes_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    CONSTRAINT fk_product_sizes_size
        FOREIGN KEY (size_id) REFERENCES sizes (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(190) NOT NULL UNIQUE,
    -- Werkzeug scrypt hashes run to ~162 chars; 255 leaves room for a change
    -- of hashing method without a migration.
    password VARCHAR(255) NOT NULL,
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
INSERT INTO sizes (name, position) VALUES
    ('Pequeno', 1), ('Médio', 2), ('Grande', 3);


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
