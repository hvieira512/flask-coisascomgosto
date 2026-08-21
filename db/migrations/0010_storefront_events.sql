-- What visitors do on the storefront.
--
-- Nothing has ever been recorded: no view counting, no request logging, no
-- third-party script. So the dashboard could say how many pieces exist and
-- nothing about whether anybody looks at them, and the owners' home page filled
-- up with second copies of what the other pages already showed.
--
-- Four kinds of event in one table rather than three tables. One write path, one
-- read path, one endpoint, for a page whose whole traffic is a village shop's;
-- most columns are NULL for most rows, which is the honest shape of an event log
-- with a few kinds. Three tables would be three of everything.
--
--   view      product_id
--   enquiry   product_id, and the colour and size the visitor had chosen
--   search    term, and how many pieces it found
--   filter    facet, and the label as it was clicked
--
-- Three decisions worth stating:
--
-- `facet_label` is text rather than an id. A filter id would point at a different
-- table depending on the facet — product_types, collections, color_sets — which no
-- foreign key can express. Storing the label the visitor actually clicked keeps it
-- to one column; a later rename shows as two rows, which at this volume is noise
-- rather than a defect.
--
-- A deleted piece takes its history with it (CASCADE): a view count for a piece
-- that no longer exists answers nothing. A deleted colour does not (SET NULL) —
-- the question was asked, and it still counts for the piece.
--
-- No identifiers. No IP address, no user agent, no cookie, no session id, and no
-- column that could hold one. The per-IP rate limit on the endpoint sees the
-- address for the length of the request and never writes it down. There is
-- nothing here to disclose in a privacy notice and nothing worth stealing.
--
-- ponytail: raw rows, no rollup. A few thousand a year is nothing to aggregate;
-- when it is something, the shape is the one `flask sweep-uploads` already uses.
CREATE TABLE storefront_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    kind VARCHAR(16) NOT NULL,
    product_id INT NULL,
    variant_id INT NULL,
    size_id INT NULL,
    facet VARCHAR(20) NULL,
    facet_label VARCHAR(120) NULL,
    term VARCHAR(120) NULL,
    results INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Every question the dashboard asks is "this kind, since this date", and the
    -- per-product one is "this piece, since this date".
    KEY idx_storefront_events_kind_time (kind, created_at),
    KEY idx_storefront_events_product (product_id, created_at),
    CONSTRAINT fk_storefront_events_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    CONSTRAINT fk_storefront_events_variant
        FOREIGN KEY (variant_id) REFERENCES product_variants (id) ON DELETE SET NULL,
    CONSTRAINT fk_storefront_events_size
        FOREIGN KEY (size_id) REFERENCES sizes (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
