"""Jinja filters for the rendered pages."""

import re
from datetime import date
from urllib.parse import urlsplit

_MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

DEFAULT_TYPE_ICON = "fa-gift"

# First match wins, so specific shapes precede generic containers.
# static/js/store/placeholder.js carries the same table — keep them in step.
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
    """An explicit icon wins; otherwise guess from the type's name, then its
    parent's, so a sub-type inherits the shape."""
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
    """"12 - 20 de Agosto de 2025", collapsing whatever the ends share.

    An unparseable value falls back to the raw string rather than breaking the
    page.
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


def social_handle(url):
    """The profile name out of a social URL: "coisascomgosto.vianadocastelo".

    The contact cards used to carry these as literals in the template, so
    changing the Instagram link in the dashboard left the shop showing the old
    handle. static/js/dashboard/contacts.js mirrors this so its preview agrees.
    """
    path = urlsplit(str(url or "")).path.strip("/")
    return path.rsplit("/", 1)[-1] or url


def register(app):
    app.jinja_env.filters["type_icon"] = type_icon
    app.jinja_env.filters["event_dates"] = event_dates
    app.jinja_env.filters["social_handle"] = social_handle
    app.jinja_env.globals["year"] = date.today().strftime("%Y")
