"""Marshalling models for products.

A product joins several catalog layers: a required product type, the materials it
is made of, an optional default size, the sizes it is available in, and one
variant per colour set it is sold in. The collections it is in are read off those
variants — a piece has no collection of its own.
"""

from flask_restx import Model, fields

from api.models.catalog import (
    collection_ref_model,
    image_model,
    product_type_nested_model,
    size_model,
    variant_model,
)
from api.models.common import list_model
from api.models.materials import material_model

product_model = Model(
    "Product",
    {
        "id": fields.Integer(readOnly=True, description="Product ID"),
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(
            required=True, description="Product Description"
        ),
        "type": fields.Nested(
            product_type_nested_model,
            description="What the object is, e.g. a Coracao with a string",
        ),
        "materials": fields.List(
            fields.Nested(material_model),
            description="What it is made of. Usually one, but a piece may mix "
            "them — a wooden base with a figure of modelling paste. Empty means "
            "nobody has classified it.",
        ),
        "collections": fields.List(
            fields.Nested(collection_ref_model),
            description="The collections this piece is in. A collection gathers "
            "colour sets, so a piece is in whichever collections gather the "
            "colour sets it is offered in — it has no collection of its own.",
        ),
        "default_size": fields.Nested(
            size_model,
            allow_null=True,
            description="Size used when no explicit size is chosen",
        ),
        "sizes": fields.List(
            fields.Nested(size_model),
            description="Sizes this product is available in. Empty means it is "
            "only sold in its default size.",
        ),
        "variants": fields.List(
            fields.Nested(variant_model),
            description="One entry per colour set this product is offered in",
        ),
        "primary_image": fields.Nested(
            image_model,
            allow_null=True,
            description="The tile image for listings: the first photograph of "
            "the first colour that has one",
        ),
    },
)

product_list_model = list_model("ProductList", "products", product_model)

product_create_model = Model(
    "ProductCreate",
    {
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(required=True, description="Product Description"),
        "type_id": fields.Integer(
            required=True, description="Product type ID"
        ),
        "material_ids": fields.List(
            fields.Integer,
            description="What the piece is made of. Omit or send an empty list "
            "for a piece nobody has classified; send several for one that mixes "
            "materials. Replaces whatever it was made of before.",
        ),
        "default_size_id": fields.Integer(description="Optional default size ID"),
    },
)

update_product_model = Model(
    "ProductUpdate",
    {
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(required=True, description="Product Description"),
        "type_id": fields.Integer(
            required=True, description="Product type ID"
        ),
        "material_ids": fields.List(
            fields.Integer,
            description="What the piece is made of. Omit or send an empty list "
            "for a piece nobody has classified; send several for one that mixes "
            "materials. Replaces whatever it was made of before.",
        ),
        "default_size_id": fields.Integer(description="Optional default size ID"),
    },
)

# One entry per filter option that has at least one product behind it.
facet_count_model = Model(
    "FacetCount",
    {
        "id": fields.Integer(description="The option's ID"),
        "count": fields.Integer(description="Products behind that option"),
    },
)

facet_counts_model = Model(
    "FacetCounts",
    {
        "types": fields.List(fields.Nested(facet_count_model)),
        "materials": fields.List(fields.Nested(facet_count_model)),
        "collections": fields.List(fields.Nested(facet_count_model)),
    },
)
