<?php

namespace App\Support;

use Illuminate\Http\JsonResponse;
use RuntimeException;

/** The file was missing, the wrong type, or too large. The message is shown to the owners. */
class UploadError extends RuntimeException
{
    public function render(): JsonResponse
    {
        return response()->json(['message' => $this->getMessage()], 400);
    }
}
