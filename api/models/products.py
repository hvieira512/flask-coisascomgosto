"""Marshalling models for products.

A product joins several catalog layers: a required product type (possibly a
sub-type), an optional material, an optional collection, an optional default size,
the sizes it is available in, and one variant per colour set it is sold in.
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
        "material": fields.Nested(
            material_model,
            allow_null=True,
            description="What it is made of; null when unclassified or mixed",
        ),
        "collection": fields.Nested(
            collection_ref_model,
            allow_null=True,
            description="Owning collection, if any",
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
        "images": fields.List(
            fields.Nested(image_model),
            description="Product-level photos, used when a variant has none",
        ),
        "primary_image": fields.Nested(
            image_model,
            allow_null=True,
            description="The tile image for listings: the first product-level "
            "photo, falling back to the first variant photo",
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
            required=True, description="Product type or sub-type ID"
        ),
        "material_id": fields.Integer(description="Optional material ID"),
        "collection_id": fields.Integer(description="Optional collection ID"),
        "default_size_id": fields.Integer(description="Optional default size ID"),
    },
)

update_product_model = Model(
    "ProductUpdate",
    {
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(required=True, description="Product Description"),
        "type_id": fields.Integer(
            required=True, description="Product type or sub-type ID"
        ),
        "material_id": fields.Integer(description="Optional material ID"),
        "collection_id": fields.Integer(description="Optional collection ID"),
        "default_size_id": fields.Integer(description="Optional default size ID"),
    },
)
