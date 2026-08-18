"""Products, plus their variants, photographs and available sizes.

A product always has a product type. It may also name what it is made of, belong
to a collection, declare a default size, list the sizes it is available in, and
carry one variant per colour set it is offered in.

One namespace, four modules — the single file had grown to 562 lines and nine
resources, and every new endpoint landed in it by default:

    products.py   the collection and the item, plus /facets
    variants.py   the colour sets a product is offered in
    images.py     photographs, uploaded or referenced by path
    sizes.py      the sizes a product is available in

Each of those imports `ns` from here, so they are imported at the bottom rather
than the top: the namespace has to exist before a module can decorate it.
"""

from flask_restx import Namespace

from api.models.catalog import (
    collection_ref_model,
    color_model,
    color_set_model,
    image_model,
    image_write_model,
    product_sizes_write_model,
    product_type_nested_model,
    size_model,
    variant_list_model,
    variant_model,
    variant_write_model,
)
from api.models.common import pagination_model
from api.models.products import (
    facet_count_model,
    facet_counts_model,
    product_create_model,
    product_list_model,
    product_model,
    update_product_model,
)

ns = Namespace("products", description="Products operations")

for model in [
    pagination_model,
    collection_ref_model,
    color_model,
    color_set_model,
    size_model,
    product_type_nested_model,
    variant_model,
    variant_list_model,
    variant_write_model,
    image_model,
    image_write_model,
    product_sizes_write_model,
    product_model,
    product_list_model,
    product_create_model,
    update_product_model,
    facet_count_model,
    facet_counts_model,
]:
    ns.models[model.name] = model

from api.routes.products import images, products, sizes, variants  # noqa: E402,F401
