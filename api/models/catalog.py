"""Marshalling models for the catalog layers.

These drive both the JSON responses and the Swagger schema at /api/docs, so the
descriptions here are the API's user-facing documentation.
"""

from flask_restx import Model, fields

from api.models.common import pagination_model

# ----------------
# Collections
# ----------------

collection_model = Model(
    "Collection",
    {
        "id": fields.Integer(readOnly=True, description="Collection ID"),
        "name": fields.String(
            required=True, description="Collection name, e.g. 'Barra da Saia'"
        ),
        "description": fields.String(description="Optional longer description"),
    },
)

collection_ref_model = Model(
    "CollectionRef",
    {
        "id": fields.Integer(description="Collection ID"),
        "name": fields.String(description="Collection name"),
    },
)

collection_list_model = Model(
    "CollectionList",
    {
        "collections": fields.List(fields.Nested(collection_model)),
        "pagination": fields.Nested(pagination_model),
    },
)

collection_write_model = Model(
    "CollectionWrite",
    {
        "name": fields.String(required=True, description="Collection name"),
        "description": fields.String(description="Optional longer description"),
    },
)

# ----------------
# Colours
# ----------------

color_model = Model(
    "Color",
    {
        "id": fields.Integer(readOnly=True, description="Colour ID"),
        "name": fields.String(required=True, description="Colour name, e.g. 'White'"),
        "hex": fields.String(description="Optional hex swatch, e.g. '#FFFFFF'"),
    },
)

color_list_model = Model(
    "ColorList",
    {
        "colors": fields.List(fields.Nested(color_model)),
        "pagination": fields.Nested(pagination_model),
    },
)

color_write_model = Model(
    "ColorWrite",
    {
        "name": fields.String(required=True, description="Colour name"),
        "hex": fields.String(description="Optional hex swatch, e.g. '#FFFFFF'"),
    },
)

# ----------------
# Colour sets
# ----------------

color_set_model = Model(
    "ColorSet",
    {
        "id": fields.Integer(readOnly=True, description="Colour set ID"),
        "name": fields.String(
            required=True, description="Colour set name, e.g. 'White and Green'"
        ),
        "collection": fields.Nested(
            collection_ref_model,
            allow_null=True,
            description="Owning collection, if any",
        ),
        "colors": fields.List(
            fields.Nested(color_model), description="Colours making up the set, ordered"
        ),
    },
)

color_set_list_model = Model(
    "ColorSetList",
    {
        "color_sets": fields.List(fields.Nested(color_set_model)),
        "pagination": fields.Nested(pagination_model),
    },
)

color_set_write_model = Model(
    "ColorSetWrite",
    {
        "name": fields.String(required=True, description="Colour set name"),
        "collection_id": fields.Integer(
            description="Owning collection ID. Omit or null for a standalone set."
        ),
        "color_ids": fields.List(
            fields.Integer,
            required=True,
            description="Colour IDs making up the set, in display order",
        ),
    },
)

# ----------------
# Sizes
# ----------------

size_model = Model(
    "Size",
    {
        "id": fields.Integer(readOnly=True, description="Size ID"),
        "name": fields.String(required=True, description="Size name, e.g. 'M'"),
        "position": fields.Integer(description="Display order, ascending"),
    },
)

size_list_model = Model(
    "SizeList",
    {
        "sizes": fields.List(fields.Nested(size_model)),
        "pagination": fields.Nested(pagination_model),
    },
)

size_write_model = Model(
    "SizeWrite",
    {
        "name": fields.String(required=True, description="Size name"),
        "position": fields.Integer(description="Display order, ascending"),
    },
)

product_sizes_write_model = Model(
    "ProductSizesWrite",
    {
        "size_ids": fields.List(
            fields.Integer,
            required=True,
            description="Full replacement set of size IDs. Empty means the "
            "product is only sold in its default size.",
        ),
    },
)

# ----------------
# Product types
# ----------------

product_type_ref_model = Model(
    "ProductTypeRef",
    {
        "id": fields.Integer(description="Product type ID"),
        "name": fields.String(description="Product type name"),
        "description": fields.String(description="Optional description"),
        "icon": fields.String(
            description="Font Awesome class drawn on products with no photo"
        ),
    },
)

product_type_model = Model(
    "ProductType",
    {
        "id": fields.Integer(readOnly=True, description="Product type ID"),
        "name": fields.String(
            required=True,
            description="What the object is, e.g. 'Hairbrush', 'Coracao'",
        ),
        "description": fields.String(description="Optional description"),
        "parent_id": fields.Integer(
            description="Parent type ID; null for a top-level type"
        ),
        "icon": fields.String(
            description="Font Awesome class, e.g. 'fa-heart'. Drawn on products "
            "that have no photo yet; null falls back to a guess from the name."
        ),
        "sub_types": fields.List(
            fields.Nested(product_type_ref_model),
            description="Sub-types, e.g. 'With string' and 'Base for mini figures'",
        ),
    },
)

product_type_list_model = Model(
    "ProductTypeList",
    {
        "product_types": fields.List(fields.Nested(product_type_model)),
        "pagination": fields.Nested(pagination_model),
    },
)

product_type_write_model = Model(
    "ProductTypeWrite",
    {
        "name": fields.String(required=True, description="Product type name"),
        "description": fields.String(description="Optional description"),
        "parent_id": fields.Integer(
            description="Parent type ID. Types nest exactly one level, so the "
            "parent must itself be a top-level type."
        ),
        "icon": fields.String(
            description="Font Awesome class, e.g. 'fa-heart' or 'fa-box'"
        ),
    },
)

# Nested inside a product: the type plus the type it sits under.
product_type_nested_model = Model(
    "ProductTypeNested",
    {
        "id": fields.Integer(description="Product type ID"),
        "name": fields.String(description="Product type name"),
        "icon": fields.String(
            description="Font Awesome class drawn on products with no photo"
        ),
        "parent": fields.Nested(
            product_type_ref_model,
            allow_null=True,
            description="Parent type when this is a sub-type",
        ),
    },
)

# ----------------
# Variants
# ----------------

image_model = Model(
    "ProductImage",
    {
        "id": fields.Integer(readOnly=True, description="Image ID"),
        "url": fields.String(required=True, description="Image URL or static path"),
        "alt": fields.String(description="Alt text for accessibility"),
        "position": fields.Integer(description="Display order, ascending"),
        "variant_id": fields.Integer(
            description="Variant this photo belongs to; null for a product-level "
            "image used as the fallback"
        ),
    },
)

image_write_model = Model(
    "ProductImageWrite",
    {
        "url": fields.String(required=True, description="Image URL or static path"),
        "alt": fields.String(description="Alt text for accessibility"),
        "position": fields.Integer(description="Display order, ascending"),
        "variant_id": fields.Integer(
            description="Attach to one variant. Omit for a product-level image."
        ),
    },
)

variant_model = Model(
    "ProductVariant",
    {
        "id": fields.Integer(readOnly=True, description="Variant ID"),
        "color_set": fields.Nested(
            color_set_model, description="The colour set this variant is offered in"
        ),
        "images": fields.List(
            fields.Nested(image_model),
            description="Photos of this specific colour set",
        ),
    },
)

variant_list_model = Model(
    "ProductVariantList",
    {"variants": fields.List(fields.Nested(variant_model))},
)

variant_write_model = Model(
    "ProductVariantWrite",
    {
        "color_set_id": fields.Integer(
            required=True, description="Colour set to offer this product in"
        ),
    },
)

CATALOG_MODELS = [
    collection_model,
    collection_ref_model,
    collection_list_model,
    collection_write_model,
    color_model,
    color_list_model,
    color_write_model,
    color_set_model,
    color_set_list_model,
    color_set_write_model,
    size_model,
    size_list_model,
    size_write_model,
    product_sizes_write_model,
    product_type_ref_model,
    product_type_model,
    product_type_list_model,
    product_type_write_model,
    product_type_nested_model,
    image_model,
    image_write_model,
    variant_model,
    variant_list_model,
    variant_write_model,
]
