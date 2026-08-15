"""Pagination: parsing request args and building the response envelope.

This is an HTTP concern, not data access, so it sits outside the repositories.
"""

from werkzeug.exceptions import BadRequest

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 100


def _positive_int(args, key: str, default: int) -> int:
    raw = args.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise BadRequest(f"'{key}' must be an integer, got {raw!r}")

    if value < 1:
        raise BadRequest(f"'{key}' must be 1 or greater, got {value}")

    return value


def get_pagination_params(args) -> tuple[int, int, int]:
    """Extract (page, limit, offset) from request args.

    Raises BadRequest (400) on non-numeric or non-positive values, and clamps
    limit to MAX_LIMIT so a single request cannot ask for the whole table.
    """
    page = _positive_int(args, "page", DEFAULT_PAGE)
    limit = min(_positive_int(args, "limit", DEFAULT_LIMIT), MAX_LIMIT)
    return page, limit, (page - 1) * limit


def make_pagination(total: int, page: int, limit: int) -> dict:
    """Build the pagination block for a list response."""
    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if limit > 0 else 0,
        "limit": limit,
    }
