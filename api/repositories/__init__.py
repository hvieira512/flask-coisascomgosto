"""Repository layer: every SQL statement in the application lives here.

One repository per table (or closely-bound group of tables). Each takes a
MySQL cursor and exposes intention-revealing methods, so route handlers never
build SQL themselves.
"""

from __future__ import annotations

from api.repositories.categories import CategoryRepository
from api.repositories.collections import CollectionRepository
from api.repositories.color_sets import ColorSetRepository
from api.repositories.contacts import ContactRepository
from api.repositories.colors import ColorRepository
from api.repositories.events import EventRepository
from api.repositories.images import ProductImageRepository
from api.repositories.product_types import (
    NestingTooDeepError,
    ProductTypeRepository,
)
from api.repositories.products import ProductRepository
from api.repositories.sizes import SizeRepository
from api.repositories.users import UserRepository
from api.repositories.variants import ProductVariantRepository

__all__ = [
    "CategoryRepository",
    "CollectionRepository",
    "ColorRepository",
    "ColorSetRepository",
    "ContactRepository",
    "EventRepository",
    "NestingTooDeepError",
    "ProductImageRepository",
    "ProductRepository",
    "ProductTypeRepository",
    "ProductVariantRepository",
    "SizeRepository",
    "UserRepository",
]
