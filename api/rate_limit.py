"""Sliding-window counters for the two endpoints anyone can reach.

Both are unauthenticated, and both would otherwise be unmetered:

    /auth/login             a password oracle — nothing counted wrong guesses
    /storefront-events      a public write — nothing stopped a flood of rows

A sliding window rather than a lockout with an expiry to store: a key is refused
while it has `allowed` hits inside `window_seconds`, and comes back on its own as
the oldest of them ages out. For logins, refusals are deliberately not counted, or
the window would never drain and the account would stay locked for as long as
somebody kept knocking.

ponytail: in process memory, so a count is per gunicorn worker (three by default)
and resets when the app restarts. With this many workers that is an honest defence
and the whole implementation is forty lines; a Redis counter is what it becomes if
it ever runs on more, and `SlidingWindow` is the seam for it.
"""

import time
from collections import defaultdict


class SlidingWindow:
    """How many times a key has come up inside the last `window_seconds`."""

    def __init__(self, allowed: int, window_seconds: int):
        self.allowed = allowed
        self.window_seconds = window_seconds
        self._hits: defaultdict[str, list[float]] = defaultdict(list)

    def _recent(self, key: str) -> list[float]:
        """This key's hits inside the window, dropping the rest.

        Pruning on read is what keeps the dict from growing without bound as
        someone works through a list of usernames or sends a burst from a new
        address every second: every key they invent expires on its own.
        """
        cutoff = time.monotonic() - self.window_seconds
        kept = [at for at in self._hits[key] if at > cutoff]

        if kept:
            self._hits[key] = kept
        else:
            del self._hits[key]

        return kept

    def is_over(self, key: str) -> bool:
        return len(self._recent(key)) >= self.allowed

    def note(self, key: str) -> None:
        self._hits[key].append(time.monotonic())

    def forget(self, key: str) -> None:
        self._hits.pop(key, None)

    def clear(self) -> None:
        """For the tests: module state outlives a test, and a lockout carried into
        the next one is a failure nobody can read."""
        self._hits.clear()


# Five wrong passwords for one username inside fifteen minutes.
logins = SlidingWindow(allowed=5, window_seconds=15 * 60)

# Sixty events from one address a minute. A visitor reading a piece sends one
# view and maybe an enquiry; sixty is a flood, and the limit costs a real shopper
# nothing.
events = SlidingWindow(allowed=60, window_seconds=60)


# The login half, named for what it means at the call site in api/routes/auth.py.
FAILURES_ALLOWED = logins.allowed
WINDOW_SECONDS = logins.window_seconds


def is_locked(username: str) -> bool:
    return logins.is_over(username)


def note_failure(username: str) -> None:
    logins.note(username)


def forget(username: str) -> None:
    """Clear the record after a successful sign-in.

    The window counts wrong guesses in a row; someone who mistyped four times and
    then got in should not be one attempt from a lockout tomorrow.
    """
    logins.forget(username)
