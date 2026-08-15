"""Jinja filters used by the rendered pages.

These are presentation concerns — how a date range reads in Portuguese, which
icon stands in for a product type — so they live with the web layer rather than
in the application entrypoint. `register` is called once from web/__init__.py.
"""

import re
from datetime import date

_MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

DEFAULT_TYPE_ICON = "fa-gift"

# Guesses a Font Awesome icon from a product type's name, for types whose owner
# has not set `icon` explicitly. Ordered: the first pattern to match wins, so
# the more specific shapes come before the generic containers.
#
# static/js/store/placeholder.js carries the same table for client-rendered
# tiles — keep the two in step.
_TYPE_ICONS = [
    (re.compile(r"cora[çc][ãa]o|heart", re.I), "fa-heart"),
    (re.compile(r"moldura|quadro|frame|foto", re.I), "fa-image"),
    (re.compile(r"bastidor|hoop", re.I), "fa-circle-notch"),
    (re.compile(r"escova|brush|cabelo", re.I), "fa-brush"),
    (re.compile(r"redond|circul|round", re.I), "fa-circle-dot"),
    (re.compile(r"caixa|box|estojo", re.I), "fa-box"),
    (re.compile(r"len[çc]o|pano|tecido|cloth", re.I), "fa-scroll"),
    (re.compile(r"[íi]man|magnet", re.I), "fa-magnet"),
    (re.compile(r"chave|key", re.I), "fa-key"),
]


def type_icon(product_type):
    """Return the Font Awesome class for a product type.

    An explicit `icon` on the type always wins. Otherwise the type's own name is
    matched against the keyword table, then its parent's — a sub-type like
    "Coracao pendurado" should fall back to the heart its parent carries.
    """
    if not product_type:
        return DEFAULT_TYPE_ICON

    if icon := (product_type.get("icon") or ""):
        return icon

    parent = product_type.get("parent") or {}
    names = " ".join(
        part for part in (product_type.get("name"), parent.get("name")) if part
    )
    for pattern, icon in _TYPE_ICONS:
        if pattern.search(names):
            return icon
    return DEFAULT_TYPE_ICON


def event_dates(starts_on, ends_on=None):
    """Format an event's date range in Portuguese for the timeline.

    Collapses the shared parts of a range: same month gives "12 - 20 de Agosto
    de 2025", a month boundary keeps both months, and an unparseable value
    falls back to the raw string rather than breaking the page.
    """

    def parse(value):
        try:
            return date.fromisoformat(str(value)[:10])
        except (TypeError, ValueError):
            return None

    start = parse(starts_on)
    if start is None:
        return starts_on or ""

    def full(d):
        return f"{d.day} de {_MONTHS_PT[d.month - 1]} de {d.year}"

    end = parse(ends_on)
    if end is None or end == start:
        return full(start)

    if start.year != end.year:
        return f"{full(start)} - {full(end)}"
    if start.month != end.month:
        return (
            f"{start.day} de {_MONTHS_PT[start.month - 1]} - "
            f"{end.day} de {_MONTHS_PT[end.month - 1]} de {end.year}"
        )
    return f"{start.day} - {end.day} de {_MONTHS_PT[start.month - 1]} de {start.year}"


def register(app):
    """Attach the filters and template globals to an application."""
    app.jinja_env.filters["type_icon"] = type_icon
    app.jinja_env.filters["event_dates"] = event_dates
    app.jinja_env.globals["year"] = date.today().strftime("%Y")
