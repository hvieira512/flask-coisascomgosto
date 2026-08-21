"""Catalog writes need a bearer token; reads stay public.

Every POST/PUT/DELETE under products, materials, collections, colours, colour
sets, types and sizes used to be open — anyone could DELETE /api/products/1.
Only contacts, events and users were guarded.
"""

import pytest

WRITES = [
    ("post", "/api/materials/", {"name": "Intruso"}),
    ("put", "/api/materials/1", {"name": "Intruso"}),
    ("delete", "/api/materials/1", None),
    # `description` is required by the model. Payloads here must be valid, or
    # flask-restx answers 400 from its own validation before the auth decorator
    # runs, and the test would pass without proving anything.
    ("post", "/api/products/", {"name": "Intruso", "description": "x", "type_id": 1}),
    ("put", "/api/products/1", {"name": "Intruso", "description": "x", "type_id": 1}),
    ("delete", "/api/products/1", None),
    ("post", "/api/colors/", {"name": "Intruso"}),
    ("delete", "/api/colors/1", None),
    ("post", "/api/collections/", {"name": "Intruso"}),
    ("delete", "/api/collections/1", None),
    ("post", "/api/product-types/", {"name": "Intruso"}),
    ("delete", "/api/product-types/1", None),
    ("post", "/api/color-sets/", {"name": "Intruso", "color_ids": [1]}),
    ("delete", "/api/color-sets/1", None),
    ("post", "/api/sizes/", {"name": "XL"}),
    ("delete", "/api/sizes/1", None),
    ("post", "/api/products/1/variants", {"color_set_id": 1}),
    ("delete", "/api/products/1/variants/1", None),
    # A valid body on purpose: flask-restx validates before the guard runs, so
    # an incomplete payload would answer 400 and never reach the thing under
    # test. variant_id is required since photographs belong to a colour.
    ("post", "/api/products/1/images", {"url": "/x.jpg", "variant_id": 1}),
    ("delete", "/api/products/1/images/1", None),
    ("put", "/api/products/1/sizes", {"size_ids": []}),
]

READS = [
    "/api/products/", "/api/materials/", "/api/colors/", "/api/collections/",
    "/api/product-types/", "/api/color-sets/", "/api/sizes/",
]


@pytest.mark.parametrize("method,path,payload", WRITES)
def test_writes_require_a_token(anon_client, method, path, payload):
    response = getattr(anon_client, method)(path, json=payload)
    assert response.status_code == 401, f"{method.upper()} {path} is open"


@pytest.mark.parametrize("path", READS)
def test_reads_stay_public(client, path):
    """The storefront is anonymous, so every list stays readable."""
    assert client.get(path).status_code == 200


def test_nothing_is_written_without_a_token(anon_client):
    anon_client.post("/api/materials/", json={"name": "Intruso"})

    names = [c["name"] for c in anon_client.get("/api/materials/").get_json()["materials"]]
    assert "Intruso" not in names


def test_an_authenticated_write_still_works(auth_client):
    response = auth_client.post("/api/materials/", json={"name": "Madeira"})
    assert response.status_code == 201
