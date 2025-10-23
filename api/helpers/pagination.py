def make_pagination(total: int, page: int, limit: int) -> dict:
    """
    Return a pagination dictionary for a response.
    """
    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "limit": limit,
    }


def get_pagination_params(args) -> tuple[int, int, int]:
    """
    Extract page, limit, and offset from Flask request args.

    Returns:
        page (int), limit (int), offset (int)
    """
    page = int(args.get("page", 1))
    limit = int(args.get("limit", 10))
    offset = (page - 1) * limit
    return page, limit, offset
