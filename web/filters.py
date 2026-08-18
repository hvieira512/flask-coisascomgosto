"""Jinja filters for the rendered pages."""

from datetime import date
from urllib.parse import urlsplit

from api.type_icons import icon_for

_MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def type_icon(product_type):
    """The Jinja filter behind the landing page's type cards. The table itself
    lives in api/type_icons.py, which the API's marshalling also uses."""
    return icon_for(product_type)


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
