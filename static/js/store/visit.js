// Counts the arrival, on whichever storefront page it happens to be. Its own
// file because base.html loads it on every page, while the modules that record
// views, enquiries and filters belong to the pages that can produce them.
import { Track } from "./track.js";

Track.visit();
