"""Data access for the shop's contact details.

This is a singleton: the table holds exactly one row (id 1), created by the
schema and edited in place. There is no phone column — the WhatsApp number is
the phone number, and `whatsapp_url` turns it into a wa.me link.
"""

from __future__ import annotations

import re
from typing import Optional

from pymysql.cursors import DictCursor

CONTACT_ID = 1

_COLUMNS = "id, address, email, whatsapp, maps_url, facebook_url, instagram_url"


class ContactRepository:
    """All SQL touching the contacts table lives here."""

    def __init__(self, cursor: DictCursor):
        self._cursor = cursor

    # ----------------
    # Queries
    # ----------------

    def get(self) -> Optional[dict]:
        """Return the contact details, or None if the row is missing."""
        self._cursor.execute(
            f"SELECT {_COLUMNS} FROM contacts WHERE id = %s", (CONTACT_ID,)
        )
        row = self._cursor.fetchone()
        return self._to_dict(row) if row else None

    # ----------------
    # Mutations
    # ----------------

    def update(
        self,
        *,
        address: Optional[str] = None,
        email: Optional[str] = None,
        whatsapp: Optional[str] = None,
        maps_url: Optional[str] = None,
        facebook_url: Optional[str] = None,
        instagram_url: Optional[str] = None,
    ) -> None:
        """Overwrite the contact details.

        Uses an upsert so the row exists even if the schema seed was skipped.
        """
        self._cursor.execute(
            "INSERT INTO contacts (id, address, email, whatsapp, maps_url, "
            "facebook_url, instagram_url) VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE address = VALUES(address), "
            "email = VALUES(email), whatsapp = VALUES(whatsapp), "
            "maps_url = VALUES(maps_url), "
            "facebook_url = VALUES(facebook_url), "
            "instagram_url = VALUES(instagram_url)",
            (
                CONTACT_ID,
                address,
                email,
                whatsapp,
                maps_url,
                facebook_url,
                instagram_url,
            ),
        )

    # ----------------
    # Internals
    # ----------------

    @staticmethod
    def whatsapp_url(number: Optional[str]) -> Optional[str]:
        """Build a wa.me link from a phone number.

        wa.me accepts digits only, so spaces, dashes and the leading + are
        stripped rather than left to break the link.
        """
        if not number:
            return None

        digits = re.sub(r"\D", "", number)
        return f"https://wa.me/{digits}" if digits else None

    @classmethod
    def _to_dict(cls, row) -> dict:
        contact = dict(row)
        contact["whatsapp_url"] = cls.whatsapp_url(contact.get("whatsapp"))
        return contact
