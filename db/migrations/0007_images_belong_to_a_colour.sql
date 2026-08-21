-- Every photograph belongs to a colour.
--
-- product_images.variant_id was nullable, and a NULL meant "of the piece as a
-- whole", shown as a fallback for any colour that had no photograph of its own.
-- That reads reasonably and works badly: a piece looks different in each
-- colourway, so the fallback showed a shopper who picked Preto e Branco a
-- photograph of the white-and-gold one. It also decided which tile the catalogue
-- listed, so the fallback quietly outranked the real photographs.
--
-- The development database had seven such rows, all of them from before colour
-- sets existed. Six showed a colourway the catalogue did not have — a navy
-- bauble, a silver-on-white frame, a pink oval frame — so those colour sets were
-- created and the photographs attached to them; the seventh, a shot of three
-- bottle openers at once, went to the colour of the one in front. That work is
-- data, not schema, so it is not repeated here.
--
-- The DELETE is for any other database: there is nothing sensible to attach a
-- colourless row to without looking at the photograph, and the file on disk is
-- left alone either way.
DELETE FROM product_images WHERE variant_id IS NULL;

ALTER TABLE product_images
    MODIFY variant_id INT NOT NULL;
