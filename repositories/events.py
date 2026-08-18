"""Data access for the events table."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Tuple

from pymysql.cursors import DictCursor

_COLUMNS = "id, name, location, description, starts_on, ends_on, url"


class EventRepository:

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    def list(
        self, *, search: Optional[str] = None, limit: int, offset: int
    ) -> list[dict]:
        where, params = self._filter(search)
        self._cursor.execute(
            f"SELECT {_COLUMNS} FROM events {where} "
            "ORDER BY starts_on DESC, id DESC LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        return [self._to_dict(row) for row in self._cursor.fetchall()]

    def count(self, *, search: Optional[str] = None) -> int:
        where, params = self._filter(search)
        self._cursor.execute(f"SELECT COUNT(*) AS total FROM events {where}", params)
        return self._cursor.fetchone()["total"]

    def get(self, event_id: int) -> Optional[dict]:
        self._cursor.execute(
            f"SELECT {_COLUMNS} FROM events WHERE id = %s", (event_id,)
        )
        row = self._cursor.fetchone()
        return self._to_dict(row) if row else None

    def exists(self, event_id: int) -> bool:
        self._cursor.execute("SELECT 1 FROM events WHERE id = %s", (event_id,))
        return self._cursor.fetchone() is not None

    def create(
        self,
        *,
        name: str,
        starts_on: str,
        location: Optional[str] = None,
        description: Optional[str] = None,
        ends_on: Optional[str] = None,
        url: Optional[str] = None,
    ) -> int:
        self._cursor.execute(
            "INSERT INTO events (name, location, description, starts_on, ends_on, url) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (name, location, description, starts_on, ends_on, url),
        )
        return self._cursor.lastrowid

    def update(
        self,
        event_id: int,
        *,
        name: str,
        starts_on: str,
        location: Optional[str] = None,
        description: Optional[str] = None,
        ends_on: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        self._cursor.execute(
            "UPDATE events SET name = %s, location = %s, description = %s, "
            "starts_on = %s, ends_on = %s, url = %s WHERE id = %s",
            (name, location, description, starts_on, ends_on, url, event_id),
        )

    def delete(self, event_id: int) -> None:
        self._cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))

    @staticmethod
    def _filter(search: Optional[str]) -> Tuple[str, list]:
        term = (search or "").strip()
        if not term:
            return "", []
        return "WHERE name LIKE %s OR location LIKE %s", [f"%{term}%", f"%{term}%"]

    @staticmethod
    def _to_dict(row) -> dict:
        """Normalise a row, keeping dates as ISO strings.

        MySQL hands DATE columns back as datetime.date objects. The API and the
        timeline template are both defined in terms of "YYYY-MM-DD", so the
        conversion happens once, here, rather than in every consumer.
        """
        event = dict(row)
        for field in ("starts_on", "ends_on"):
            value = event.get(field)
            if isinstance(value, (date, datetime)):
                event[field] = value.isoformat()[:10]

        # The timeline groups by year, so derive it rather than making every
        # caller parse the date string.
        starts_on = event.get("starts_on") or ""
        event["year"] = starts_on[:4] if len(starts_on) >= 4 else None
        return event
