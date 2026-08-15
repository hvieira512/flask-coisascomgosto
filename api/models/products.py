"""Marshalling models for products.

A product joins several catalog layers: a required category, an optional product
type (possibly a sub-type), an optional collection, an optional default size, the
sizes it is available in, and one variant per colour set it is sold in.
"""

from flask_restx import Model, fields

from api.models.categories import category_model
from api.models.catalog import (
    collection_ref_model,
    image_model,
    product_type_nested_model,
    size_model,
    variant_model,
)
from api.models.common import pagination_model

product_model = Model(
    "Product",
    {
        "id": fields.Integer(readOnly=True, description="Product ID"),
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(
            required=True, description="Product Description"
        ),
        "category": fields.Nested(category_model, description="Owning category"),
        "type": fields.Nested(
            product_type_nested_model,
            allow_null=True,
            description="What the object is, e.g. a Coracao with a string",
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

product_list_model = Model(
    "ProductList",
    {
        "products": fields.List(fields.Nested(product_model)),
        "pagination": fields.Nested(pagination_model),
    },
)

product_create_model = Model(
    "ProductCreate",
    {
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(required=True, description="Product Description"),
        "category_id": fields.Integer(required=True, description="Product Category ID"),
        "type_id": fields.Integer(description="Optional product type or sub-type ID"),
        "collection_id": fields.Integer(description="Optional collection ID"),
        "default_size_id": fields.Integer(description="Optional default size ID"),
    },
)

update_product_model = Model(
    "ProductUpdate",
    {
        "name": fields.String(required=True, description="Product Name"),
        "description": fields.String(required=True, description="Product Description"),
        "category_id": fields.Integer(required=True, description="Product Category ID"),
        "type_id": fields.Integer(description="Optional product type or sub-type ID"),
        "collection_id": fields.Integer(description="Optional collection ID"),
        "default_size_id": fields.Integer(description="Optional default size ID"),
    },
)
