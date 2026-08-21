-- Removing a photograph deleted the file off the disk, in the same request.
--
-- For people whose only copy of a photograph may be the one they uploaded from a
-- phone two years ago, a mis-tap was unrecoverable. The confirmations are good —
-- they name the count — but a confirmation is not a backup.
--
-- So a removed photograph keeps its row, marked, and the file stays where it is.
-- Every read filters on deleted_at IS NULL, so the storefront and the dashboard
-- behave exactly as before; restoring one is an UPDATE.
--
-- The rest of the story is in uploads.sweep(), which is now the only thing in the
-- application that deletes a file: `flask sweep-uploads` purges rows marked more
-- than thirty days ago and then removes files no row points at any more. Deleting
-- a piece or a colour still removes those rows outright (the foreign keys cascade,
-- and a soft-deleted child of a hard-deleted parent is a state nothing could
-- present), but the photographs themselves survive on disk until the sweep, which
-- is the part that was irreversible.
ALTER TABLE product_images
    ADD COLUMN deleted_at DATETIME NULL,
    ADD KEY idx_product_images_deleted (deleted_at);
