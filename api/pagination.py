"""Request-arg parsing and the pagination response envelope."""

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
    """(page, limit, offset), 400 on bad input, limit clamped to MAX_LIMIT."""
    page = _positive_int(args, "page", DEFAULT_PAGE)
    limit = min(_positive_int(args, "limit", DEFAULT_LIMIT), MAX_LIMIT)
    return page, limit, (page - 1) * limit


def make_pagination(total: int, page: int, limit: int) -> dict:
    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if limit > 0 else 0,
        "limit": limit,
    }
