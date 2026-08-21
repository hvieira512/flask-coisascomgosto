"""The three bodies every list-and-lookup namespace was repeating.

Each namespace keeps its own decorator stack, because that is what documents its
HTTP surface in Swagger and is worth reading resource by resource. What was
worth sharing is underneath: paging a search, and the two checks that turn a
missing row or a taken name into the right status code.
"""

from typing import NoReturn

from flask import request
from flask_restx._http import HTTPStatus

from api.pagination import get_pagination_params, make_pagination

# The 201 every create returns.
#
# flask-restx does not use the standard library's HTTPStatus: it carries a
# backport of Python 3.5's in flask_restx._http, and that is the type its
# marshal_with() signature names. So `code=201` and `code=http.HTTPStatus.CREATED`
# are both the wrong type as far as a checker is concerned, though either works at
# runtime — the enum is an IntEnum whose str() is "201", which is what keeps the
# Swagger document's response keys numeric.
#
# Imported from a private module here and nowhere else, so twelve call sites can
# name it without twelve suppressions or nine private imports.
CREATED = HTTPStatus.CREATED


def bail(ns, code: int, message: str) -> NoReturn:
    """Abort the request, and say so in the signature.

    flask-restx's own abort raises — that is its whole job — but it is typed as
    returning None, so every guard written as

        if not row:
            ns.abort(404, "…")
        use(row)

    reads to a type checker as code that carries on with a row it just called
    absent. Eight of those, and two more where the value assigned in a `try` was
    reported unbound below the `except`. NoReturn tells the checker what the
    function already does, which is cheaper than a `raise` after every abort.
    """
    ns.abort(code, message)
    # Unreachable: abort raises. Here so the body satisfies NoReturn on its own
    # terms rather than on trust.
    raise AssertionError(f"ns.abort({code}) returned")


def page_of(repository, key: str, **filters) -> dict:
    """A page of rows under `key`, alongside its pagination envelope.

    Reads `page`, `limit` and `q` straight off the query string. Any narrowing
    beyond the search term — a parent type, a collection — is a filter the route
    has already parsed, and reaches both list() and count() so the total matches
    what was returned.
    """
    page, limit, offset = get_pagination_params(request.args)
    search = request.args.get("q")

    return {
        key: repository.list(search=search, limit=limit, offset=offset, **filters),
        "pagination": make_pagination(
            repository.count(search=search, **filters), page, limit
        ),
    }


def get_or_404(ns, repository, row_id: int, label: str) -> dict:
    row = repository.get(row_id)
    if not row:
        bail(ns, 404, f"{label} #{row_id} not found")
    return row


def reject_duplicate_name(ns, repository, name: str, label: str, *, exclude_id=None):
    """409 when the name is taken.

    `exclude_id` is what lets an update keep its own name: without it every
    rename would collide with the row being renamed.
    """
    if not repository.name_exists(name, exclude_id=exclude_id):
        return

    if exclude_id is None:
        ns.abort(409, f"The {label.lower()} '{name}' already exists.")
    ns.abort(409, f"{label} name '{name}' is already used by another {label.lower()}.")
