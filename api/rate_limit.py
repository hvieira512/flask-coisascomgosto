"""A failed-login counter.

/auth/login is an unmetered password oracle otherwise: the accounts belong to two
people, the passwords are whatever they chose, and nothing anywhere counts how
many times a guess has been wrong.

A sliding window rather than a lockout with an expiry to store: an account is
refused while it has FAILURES_ALLOWED failures inside WINDOW_SECONDS, and comes
back on its own as the oldest of them ages out. Refusals are not themselves
counted, or the window would never drain and the account would be locked out for
as long as someone kept knocking.

ponytail: in process memory, so the count is per gunicorn worker and resets when
the app restarts. With one or two workers that is an honest defence and the whole
implementation is thirty lines; a Redis counter is what this becomes if it ever
runs on more, and the two functions below are the seam for it.
"""

import time
from collections import defaultdict

FAILURES_ALLOWED = 5
WINDOW_SECONDS = 15 * 60

_failures: defaultdict[str, list[float]] = defaultdict(list)


def _recent(username: str) -> list[float]:
    """This account's failures inside the window, dropping the rest.

    Pruning on read keeps the dict from growing without bound as someone works
    through a list of usernames — every key they invent expires on its own.
    """
    cutoff = time.monotonic() - WINDOW_SECONDS
    kept = [at for at in _failures[username] if at > cutoff]

    if kept:
        _failures[username] = kept
    else:
        del _failures[username]

    return kept


def is_locked(username: str) -> bool:
    return len(_recent(username)) >= FAILURES_ALLOWED


def note_failure(username: str) -> None:
    _failures[username].append(time.monotonic())


def forget(username: str) -> None:
    """Clear the record after a successful sign-in.

    The window counts wrong guesses in a row; someone who mistyped four times and
    then got in should not be one attempt from a lockout tomorrow.
    """
    _failures.pop(username, None)
