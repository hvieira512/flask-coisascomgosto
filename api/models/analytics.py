from flask_restx import Model, fields

window_model = Model(
    "AnalyticsWindow",
    {
        "days": fields.Integer(description="How many days the figures cover"),
        "counting_since": fields.String(
            description="When the first event was ever recorded, or null if none "
            "has been. Before this date there is no history to show, which is a "
            "different thing from a quiet week."
        ),
    },
)

totals_model = Model(
    "AnalyticsTotals",
    {
        "views": fields.Integer(description="Pieces opened"),
        "enquiries": fields.Integer(description="Times somebody asked about one"),
        "searches": fields.Integer(description="Searches made"),
        "pieces": fields.Integer(
            description="How many different pieces were opened — how much of the "
            "catalogue got any attention at all"
        ),
    },
)

viewed_product_model = Model(
    "AnalyticsViewedProduct",
    {
        "id": fields.Integer(description="Product ID"),
        "name": fields.String(description="Product name"),
        "views": fields.Integer(description="Times it was opened"),
        "enquiries": fields.Integer(
            description="Times somebody asked about it. Beside the views on "
            "purpose: interest that never becomes a question is a different "
            "problem from no interest."
        ),
    },
)

asked_color_set_model = Model(
    "AnalyticsAskedColorSet",
    {
        "id": fields.Integer(description="Colour set ID"),
        "name": fields.String(description="Colour set name"),
        "enquiries": fields.Integer(description="Times it was the colour asked for"),
    },
)

empty_search_model = Model(
    "AnalyticsEmptySearch",
    {
        "term": fields.String(description="What was typed"),
        "count": fields.Integer(description="How many times, finding nothing"),
    },
)

used_filter_model = Model(
    "AnalyticsUsedFilter",
    {
        "facet": fields.String(description="Which group: Tipo, Material, Colecção"),
        "label": fields.String(description="Which option, as the owners named it"),
        "count": fields.Integer(description="Times it was ticked"),
    },
)

catalogue_model = Model(
    "AnalyticsCatalogue",
    {
        "products": fields.Integer(description="Pieces in the catalogue"),
        "color_sets": fields.Integer(description="Colour sets"),
        "collections": fields.Integer(description="Collections"),
        "colors": fields.Integer(description="Individual colours"),
        "added": fields.Integer(
            description="Pieces added during the window, or null when the window "
            "begins before pieces were dated at all — every row that predates "
            "migration 0011 carries the date that migration ran, so an earlier "
            "window would report the whole back catalogue as new"
        ),
    },
)

overview_model = Model(
    "AnalyticsOverview",
    {
        "window": fields.Nested(window_model),
        "totals": fields.Nested(totals_model, description="This window"),
        "previous": fields.Nested(
            totals_model,
            description="The window before this one, so each figure can say which "
            "way it is going",
        ),
        "top_products": fields.List(fields.Nested(viewed_product_model)),
        "top_color_sets": fields.List(fields.Nested(asked_color_set_model)),
        "empty_searches": fields.List(fields.Nested(empty_search_model)),
        "top_filters": fields.List(fields.Nested(used_filter_model)),
        "catalogue": fields.Nested(
            catalogue_model,
            description="How big the catalogue is, so the page can orient without "
            "a second request",
        ),
    },
)

ANALYTICS_MODELS = [
    window_model,
    totals_model,
    viewed_product_model,
    asked_color_set_model,
    empty_search_model,
    used_filter_model,
    catalogue_model,
    overview_model,
]
