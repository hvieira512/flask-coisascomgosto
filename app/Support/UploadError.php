<?php

namespace App\Support;

use Illuminate\Http\JsonResponse;
use RuntimeException;

/** The file was missing, the wrong type, or too large. The message is shown to the owners. */
class UploadError extends RuntimeException
{
    /** The caller's mistake, not the server's: nothing for the log. */
    public function report(): bool
    {
        return true;
    }

    public function render(): JsonResponse
    {
        return response()->json(['message' => $this->getMessage()], 400);
    }
}
