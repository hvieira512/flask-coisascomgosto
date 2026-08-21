"""Recording what a visitor did. The one endpoint the storefront writes to.

Public, because the visitor is not signed in and never will be. That makes it the
first unauthenticated write outside /auth, so it carries the same two defences
/auth/login does, in the same order: a rate limit before anything else, and a
header a crawler cannot set.

It answers 204 and nothing else. There is nothing to tell the caller — the page
does not read the result, and a counter that puts an error in a shopper's console
is worse than a counter that missed one event. So an id that does not exist is
dropped rather than refused, and only a malformed *request* is a 400.
"""

from flask import request
from flask_restx import Namespace, Resource

from db import get_db_connection
from api import rate_limit
from api.models.storefront_events import storefront_event_write_model
from api.routes.crud import bail
from api.security import REQUIRED_HEADER
from repositories import (
    AnalyticsRepository,
    ProductRepository,
    ProductVariantRepository,
    SizeRepository,
)

ns = Namespace(
    "storefront-events",
    description="What visitors do on the storefront. Counters only — no "
    "identifiers are stored, and the table has no column that could hold one.",
)

ns.models[storefront_event_write_model.name] = storefront_event_write_model


@ns.route("/")
class StorefrontEventList(Resource):
    @ns.expect(storefront_event_write_model, validate=True)
    @ns.response(204, "Recorded, or quietly ignored")
    @ns.response(400, "Unknown kind, or a malformed body")
    @ns.response(403, f"Missing the {REQUIRED_HEADER} header")
    @ns.response(429, "Too many events from this address")
    def post(self):
        """Record one storefront event."""
        # First, before any work: the same shape as /auth/login. remote_addr is the
        # real address — there is no proxy in front of this app, so no
        # X-Forwarded-For to weigh — and it is used here and never written down.
        caller = request.remote_addr or "unknown"
        if rate_limit.events.is_over(caller):
            bail(ns, 429, "Too many events. Slow down.")
        rate_limit.events.note(caller)

        # A crawler cannot set a header outside the CORS safelist, and a
        # cross-site form cannot set one at all — the same reasoning as
        # api/security.py's guard on session writes. Counting from the browser is
        # the other half of the bot filter.
        if REQUIRED_HEADER not in request.headers:
            bail(ns, 403, f"{REQUIRED_HEADER} header required")

        # `kind` needs no check here: the write model's enum is built from KINDS
        # itself, so validation refuses anything else with a 400 naming the four,
        # and the repository raises if it is ever reached another way.
        data = ns.payload

        with get_db_connection() as (_, cursor):
            product_id = data.get("product_id")
            if product_id is not None and not ProductRepository(cursor).exists(
                product_id
            ):
                # The piece was deleted between the page loading and this arriving,
                # or somebody is poking at the endpoint. Either way there is
                # nothing to count and nothing to say.
                return "", 204

            # Record the enquiry, forget the colour: a colour belonging to another
            # piece — or named with no piece at all — is a client bug, and losing
            # the whole event would hide it twice over.
            variant_id = data.get("variant_id")
            if variant_id is not None and (
                product_id is None
                or not ProductVariantRepository(cursor).belongs_to(
                    variant_id, product_id
                )
            ):
                variant_id = None

            size_id = data.get("size_id")
            if size_id is not None and not SizeRepository(cursor).exists(size_id):
                size_id = None

            AnalyticsRepository(cursor).record(
                data["kind"],
                product_id=product_id,
                variant_id=variant_id,
                size_id=size_id,
                facet=data.get("facet"),
                facet_label=data.get("facet_label"),
                term=data.get("term"),
                results=data.get("results"),
            )

        return "", 204
