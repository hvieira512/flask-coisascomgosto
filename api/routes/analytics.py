"""What the dashboard's home page reads.

One request, aggregated in SQL. The page it feeds used to make six and count in
the browser, which is why it inherited the API's hundred-row ceiling and would
have started quietly lying at the hundred-and-first piece. A GROUP BY has no
ceiling.

Guarded: this is the owners' own reading of their shop. The recording half is
public — see storefront_events.py — because the visitor doing the thing is not
signed in.
"""

from flask import request
from flask_restx import Namespace, Resource

from db import get_db_connection
from api.models.analytics import ANALYTICS_MODELS, overview_model
from api.security import PROTECTED_DOC, auth_required
from repositories import (
    AnalyticsRepository,
    CollectionRepository,
    ColorRepository,
    ColorSetRepository,
    ProductRepository,
)

ns = Namespace("analytics", description="What visitors do, for the dashboard")

for model in ANALYTICS_MODELS:
    ns.models[model.name] = model

# The windows the dashboard offers. Anything between a day and a year is
# answerable, so the parameter is clamped rather than refused: a hand-typed
# ?days=14 is a reasonable question, and 400 for it would be pedantry.
DEFAULT_DAYS = 7
MAX_DAYS = 365


@ns.route("/overview")
class AnalyticsOverview(Resource):
    @ns.marshal_with(overview_model)
    @ns.param("days", f"How many days to cover (1–{MAX_DAYS}, default {DEFAULT_DAYS})")
    @ns.response(200, "Everything the home page shows, for one window")
    @ns.doc(**PROTECTED_DOC)
    @auth_required
    def get(self):
        """Views, enquiries, searches and filters over a window, aggregated."""
        # No `or DEFAULT_DAYS` here: ?days=0 is falsy, so that swallowed the clamp
        # and answered a week. Flask returns the default when the value will not
        # convert, so this is never None.
        days = request.args.get("days", default=DEFAULT_DAYS, type=int)
        days = max(1, min(days, MAX_DAYS))

        with get_db_connection() as (_, cursor):
            analytics = AnalyticsRepository(cursor)
            overview = analytics.overview(days=days)

            # Composed here rather than in the analytics repository: these are
            # four ordinary counts of the catalogue's own tables, and the reason
            # they ride along is that the page should cost one request, not that
            # they are anything to do with visitors.
            overview["catalogue"] = {
                "products": ProductRepository(cursor).count(),
                "color_sets": ColorSetRepository(cursor).count(),
                "collections": CollectionRepository(cursor).count(),
                "colors": ColorRepository(cursor).count(),
                # None when the window reaches back before pieces had a date at
                # all, which the page reads as "leave the phrase out".
                "added": analytics.pieces_added(days),
            }

            return overview
