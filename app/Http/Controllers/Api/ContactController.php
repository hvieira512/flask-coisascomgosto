<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\ContactResource;
use App\Models\Contact;
use Illuminate\Http\Request;

/**
 * The shop's own details. One record, so no id in the URL. The public pages
 * read it server-side, so even the GET is guarded.
 */
class ContactController extends Controller
{
    private const FIELDS = ['address', 'email', 'whatsapp', 'maps_url', 'facebook_url', 'instagram_url'];

    public function show(): ContactResource
    {
        return new ContactResource(Contact::shop() ?? $this->fail(404, 'Contact details have not been set up.'));
    }

    /** Replace them. Every field is optional, and omitting one clears it. */
    public function update(Request $request): ContactResource
    {
        $data = $this->payload($request, array_fill_keys(self::FIELDS, ['sometimes', 'string']));

        // An upsert, so the row exists even if the schema's seed was skipped.
        Contact::updateOrCreate(['id' => 1], array_merge(array_fill_keys(self::FIELDS, null), $data));

        return new ContactResource(Contact::shop());
    }
}
