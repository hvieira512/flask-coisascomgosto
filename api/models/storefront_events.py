from flask_restx import Model, fields

from repositories.analytics import KINDS

storefront_event_write_model = Model(
    "StorefrontEventWrite",
    {
        "kind": fields.String(
            required=True,
            enum=list(KINDS),
            description="What happened: view (a piece was opened), enquiry (it "
            "was asked about), search, or filter.",
        ),
        "product_id": fields.Integer(
            description="The piece, on a view or an enquiry. An id that does not "
            "exist is ignored rather than refused — a counter must not put an "
            "error in a shopper's console."
        ),
        "variant_id": fields.Integer(
            description="On an enquiry: the colour the visitor had chosen. This is "
            "the field that tells the owners what to make next."
        ),
        "size_id": fields.Integer(description="On an enquiry: the size chosen."),
        "facet": fields.String(
            description="On a filter: which group was ticked — tipo, colecção, cor "
            "or material."
        ),
        "facet_label": fields.String(
            description="On a filter: the label as it was clicked. A label rather "
            "than an id, because an id would point at a different table per facet."
        ),
        "term": fields.String(
            description="On a search: what was typed. Lowercased and "
            "whitespace-collapsed on the way in, so two spellings of one search do "
            "not split its count."
        ),
        "results": fields.Integer(
            description="On a search: how many pieces it found. Zero is the "
            "interesting value — it is a list of things people want and the "
            "catalogue does not offer."
        ),
    },
)
