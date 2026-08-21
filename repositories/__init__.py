"""Repository layer: every SQL statement in the application lives here.

Top-level, not under api/: the REST API is one caller, and the storefront's page
routes, the seed and the create-user command are the others.

One repository per table (or closely-bound group of tables). Each takes a
MySQL cursor and exposes intention-revealing methods, so route handlers never
build SQL themselves.
"""

from __future__ import annotations

from repositories.analytics import AnalyticsRepository
from repositories.collections import CollectionRepository
from repositories.color_sets import ColorSetRepository
from repositories.contacts import ContactRepository
from repositories.colors import ColorRepository
from repositories.events import EventRepository
from repositories.images import ProductImageRepository
from repositories.materials import MaterialRepository
from repositories.product_types import ProductTypeRepository
from repositories.products import ProductRepository
from repositories.sizes import SizeRepository
from repositories.users import UserRepository
from repositories.variants import ProductVariantRepository

__all__ = [
    "AnalyticsRepository",
    "CollectionRepository",
    "ColorRepository",
    "ColorSetRepository",
    "ContactRepository",
    "EventRepository",
    "MaterialRepository",
    "ProductImageRepository",
    "ProductRepository",
    "ProductTypeRepository",
    "ProductVariantRepository",
    "SizeRepository",
    "UserRepository",
]
