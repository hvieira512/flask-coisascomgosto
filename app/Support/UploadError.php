<?php

namespace App\Support;

use RuntimeException;

/** The file was missing, the wrong type, or too large. The message is shown to the owners. */
class UploadError extends RuntimeException {}
