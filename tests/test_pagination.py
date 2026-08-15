"""Unit tests for api.pagination."""

import pytest
from werkzeug.exceptions import BadRequest

from api.pagination import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    get_pagination_params,
    make_pagination,
)


class TestGetPaginationParams:
    def test_defaults_when_args_empty(self):
        assert get_pagination_params({}) == (1, DEFAULT_LIMIT, 0)

    def test_offset_derived_from_page_and_limit(self):
        assert get_pagination_params({"page": "3", "limit": "5"}) == (3, 5, 10)

    def test_limit_is_clamped_to_max(self):
        page, limit, offset = get_pagination_params({"limit": "10000"})
        assert limit == MAX_LIMIT
        assert (page, offset) == (1, 0)

    @pytest.mark.parametrize("value", ["abc", "1.5", ""])
    def test_non_integer_rejected(self, value):
        with pytest.raises(BadRequest):
            get_pagination_params({"page": value})

    @pytest.mark.parametrize("value", ["0", "-1"])
    def test_non_positive_rejected(self, value):
        with pytest.raises(BadRequest):
            get_pagination_params({"page": value})
        with pytest.raises(BadRequest):
            get_pagination_params({"limit": value})


class TestMakePagination:
    def test_page_count_rounds_up(self):
        assert make_pagination(total=21, page=1, limit=10)["pages"] == 3

    def test_exact_multiple_does_not_add_a_page(self):
        assert make_pagination(total=20, page=1, limit=10)["pages"] == 2

    def test_zero_total_has_no_pages(self):
        assert make_pagination(total=0, page=1, limit=10)["pages"] == 0

    def test_echoes_page_and_limit(self):
        assert make_pagination(total=5, page=2, limit=3) == {
            "total": 5,
            "page": 2,
            "pages": 2,
            "limit": 3,
        }
