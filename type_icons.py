"""The icon drawn on a piece that has no photograph yet.

A type may carry an explicit Font Awesome class, chosen by the owners on the
Tipos page. When it does not, one is guessed from its name.

This is the only copy of that table. It used to exist twice — here in Python for
the server-rendered pages and again in static/js/store/placeholder.js for the
ones the browser builds — with a comment in each asking the reader to keep them
in step, which is a promise rather than a mechanism. Product responses now carry
a resolved icon, so the browser has nothing left to guess.

Deliberately not resolved on /product-types itself: the dashboard's form shows
"Adivinhar pelo nome" for a type with no icon, and it can only offer that while it
can still tell a guess from a choice.
"""

import re

DEFAULT = "fa-gift"

# First match wins, so specific shapes precede generic containers.
_ICONS = [
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


def icon_for(product_type) -> str:
    """An explicit icon wins; otherwise guess from the type's name."""
    if not product_type:
        return DEFAULT

    if icon := (product_type.get("icon") or ""):
        return icon

    name = product_type.get("name") or ""
    for pattern, icon in _ICONS:
        if pattern.search(name):
            return icon
    return DEFAULT
