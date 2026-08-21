"""Data access for what visitors do on the storefront.

One table, `storefront_events`, holding four kinds of event: a piece opened, a
piece asked about (with the colour and size chosen), a search (with how many
pieces it found), and a filter ticked.

Counters only. Nothing here records anything about the person — the table has no
column that could hold an identifier, which `tests/test_storefront_events_api.py`
asserts rather than trusting this docstring.
"""

from __future__ import annotations

from typing import Optional

from pymysql.cursors import DictCursor

from repositories.base import one_row

# What a caller may record. Anything else is a bug in a caller, not a new kind of
# event to be tolerated: the dashboard reads these four names and nothing else,
# so an unrecognised one would accumulate rows nobody ever looks at.
KINDS = ("view", "enquiry", "search", "filter")

# A search term is stored to compare with other search terms, so it is normalised
# once here rather than at every read.
TERM_MAX = 120


class AnalyticsRepository:

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    # ----------------
    # Recording
    # ----------------

    def record(
        self,
        kind: str,
        *,
        product_id: Optional[int] = None,
        variant_id: Optional[int] = None,
        size_id: Optional[int] = None,
        facet: Optional[str] = None,
        facet_label: Optional[str] = None,
        term: Optional[str] = None,
        results: Optional[int] = None,
    ) -> None:
        """Write one event. Everything but `kind` is optional, by kind."""
        if kind not in KINDS:
            raise ValueError(f"unknown event kind: {kind!r}")

        self._cursor.execute(
            "INSERT INTO storefront_events "
            "(kind, product_id, variant_id, size_id, facet, facet_label, term, results) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                kind,
                product_id,
                variant_id,
                size_id,
                facet,
                tidy(facet_label) if facet_label else None,
                normalise_term(term) if term else None,
                results,
            ),
        )

    def count(self, kind: Optional[str] = None) -> int:
        """How many events there are, for the tests and the empty state."""
        if kind is None:
            self._cursor.execute("SELECT COUNT(*) AS total FROM storefront_events")
        else:
            self._cursor.execute(
                "SELECT COUNT(*) AS total FROM storefront_events WHERE kind = %s",
                (kind,),
            )
        return one_row(self._cursor)["total"]

    def counting_since(self) -> Optional[str]:
        """When the first event was recorded, or None if nothing has been.

        The page needs it: before there is history, "0 vistas" reads as a broken
        page, and "a contagem começou hoje" reads as the truth.
        """
        self._cursor.execute(
            "SELECT MIN(created_at) AS started FROM storefront_events"
        )
        started = one_row(self._cursor)["started"]
        return started.isoformat() if started else None


def tidy(text: str) -> str:
    """Collapse whitespace and cut to what the column holds."""
    return " ".join(text.split())[:TERM_MAX]


def normalise_term(text: str) -> str:
    """The same, lowercased, for a search term.

    Lowercased because "Caixa" and "caixa" are the same search as far as anyone
    reading the list is concerned, and two rows would split the count. A filter
    label is *not* lowercased: it is a name the owners gave something — Filigrana,
    Caixa — and it comes from the database already spelled one way, so there is
    nothing to collapse and "filigrana" in the dashboard would just look wrong.
    """
    return tidy(text).lower()
