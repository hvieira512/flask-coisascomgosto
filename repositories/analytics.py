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


    # ----------------
    # Reading: one window's worth of everything the dashboard shows
    # ----------------

    def overview(self, *, days: int, top: int = 8) -> dict:
        """Everything the home page shows, for the last `days` days.

        Aggregated here rather than in the browser. The page used to filter the
        whole catalogue client-side, which is why it inherited the API's
        hundred-row ceiling and would have started lying at the hundred-and-first
        piece; a GROUP BY has no such limit and this is one request instead of six.
        """
        return {
            "window": {
                "days": days,
                "counting_since": self.counting_since(),
            },
            "totals": self._totals(days, 0),
            # The same window, one window earlier, so each figure can say which
            # way it is going. A number with nothing to compare it to is a number
            # nobody can act on.
            "previous": self._totals(days, days),
            "top_products": self._top_products(days, top),
            "top_color_sets": self._top_color_sets(days, top),
            "empty_searches": self._empty_searches(days, top),
            "top_filters": self._top_filters(days, top),
        }

    def _since(self, days: int, offset_days: int) -> tuple[str, list]:
        """The WHERE clause for a window, and its parameters.

        `offset_days` shifts it back a whole window, which is how the previous
        period is asked for with the same SQL.

        The current window has no upper bound on purpose. `created_at < NOW()`
        looks equivalent and is not: DATETIME keeps whole seconds, so an event
        recorded in the same second as the query has a timestamp equal to NOW()
        and would be excluded — which made this miss the event that had just
        happened, and only sometimes, depending on where the second boundary fell.
        """
        if offset_days == 0:
            return "created_at >= NOW() - INTERVAL %s DAY", [days]

        return (
            "created_at >= NOW() - INTERVAL %s DAY "
            "AND created_at < NOW() - INTERVAL %s DAY",
            [days + offset_days, offset_days],
        )

    def _totals(self, days: int, offset_days: int) -> dict:
        where, params = self._since(days, offset_days)
        self._cursor.execute(
            "SELECT "
            "  SUM(kind = 'view') AS views, "
            "  SUM(kind = 'enquiry') AS enquiries, "
            "  SUM(kind = 'search') AS searches, "
            "  COUNT(DISTINCT CASE WHEN kind = 'view' THEN product_id END) AS pieces "
            f"FROM storefront_events WHERE {where}",
            params,
        )
        row = one_row(self._cursor)
        # SUM() over no rows is NULL, and the page wants a number.
        return {key: int(row[key] or 0) for key in ("views", "enquiries", "searches", "pieces")}

    def _top_products(self, days: int, top: int) -> list[dict]:
        """The pieces people looked at, with how often they then asked.

        Both counts in one pass: the two side by side are the interesting part —
        interest that never turns into a question is a different problem from no
        interest at all.
        """
        where, params = self._since(days, 0)
        self._cursor.execute(
            "SELECT p.id AS id, p.name AS name, "
            "       SUM(e.kind = 'view') AS views, "
            "       SUM(e.kind = 'enquiry') AS enquiries "
            "FROM storefront_events e "
            "JOIN products p ON p.id = e.product_id "
            f"WHERE {where} AND e.kind IN ('view', 'enquiry') "
            "GROUP BY p.id, p.name "
            "ORDER BY views DESC, enquiries DESC, p.name "
            "LIMIT %s",
            params + [top],
        )
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "views": int(row["views"] or 0),
                "enquiries": int(row["enquiries"] or 0),
            }
            for row in self._cursor.fetchall()
        ]

    def _top_color_sets(self, days: int, top: int) -> list[dict]:
        """Which colourways get asked about. The answer to "what do we make next"."""
        where, params = self._since(days, 0)
        self._cursor.execute(
            "SELECT cs.id AS id, cs.name AS name, COUNT(*) AS enquiries "
            "FROM storefront_events e "
            "JOIN product_variants v ON v.id = e.variant_id "
            "JOIN color_sets cs ON cs.id = v.color_set_id "
            f"WHERE {where} AND e.kind = 'enquiry' "
            "GROUP BY cs.id, cs.name "
            "ORDER BY enquiries DESC, cs.name "
            "LIMIT %s",
            params + [top],
        )
        return [
            {"id": row["id"], "name": row["name"], "enquiries": int(row["enquiries"])}
            for row in self._cursor.fetchall()
        ]

    def _empty_searches(self, days: int, top: int) -> list[dict]:
        """What people looked for and did not find — a list of things to consider
        making, in their own words."""
        where, params = self._since(days, 0)
        self._cursor.execute(
            "SELECT term, COUNT(*) AS count FROM storefront_events "
            f"WHERE {where} AND kind = 'search' AND results = 0 AND term IS NOT NULL "
            "GROUP BY term ORDER BY count DESC, term LIMIT %s",
            params + [top],
        )
        return [
            {"term": row["term"], "count": int(row["count"])}
            for row in self._cursor.fetchall()
        ]

    def _top_filters(self, days: int, top: int) -> list[dict]:
        where, params = self._since(days, 0)
        self._cursor.execute(
            "SELECT facet, facet_label AS label, COUNT(*) AS count "
            "FROM storefront_events "
            f"WHERE {where} AND kind = 'filter' AND facet_label IS NOT NULL "
            "GROUP BY facet, facet_label ORDER BY count DESC, facet, facet_label "
            "LIMIT %s",
            params + [top],
        )
        return [
            {
                "facet": row["facet"],
                "label": row["label"],
                "count": int(row["count"]),
            }
            for row in self._cursor.fetchall()
        ]


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
