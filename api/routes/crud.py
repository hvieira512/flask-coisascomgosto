"""The three bodies every list-and-lookup namespace was repeating.

Each namespace keeps its own decorator stack, because that is what documents its
HTTP surface in Swagger and is worth reading resource by resource. What was
worth sharing is underneath: paging a search, and the two checks that turn a
missing row or a taken name into the right status code.
"""

from flask import request

from api.pagination import get_pagination_params, make_pagination


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
        ns.abort(404, f"{label} #{row_id} not found")
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
